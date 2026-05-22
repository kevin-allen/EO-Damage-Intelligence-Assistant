# Software Architecture — EO Damage Intelligence Assistant

Status: **draft v0.1** — working strawman to be reviewed/edited collaboratively.

Companion to [`software_requirements.md`](./software_requirements.md). This document describes *how* we will build what that document says we will build.

## 1. Overview

The system is a two-container application:

- **`app`** — a Streamlit web app that owns the UI, CV inference (PyTorch), aggregation, RAG retrieval (ChromaDB + sentence-transformers), and the LLM client (HTTP to Ollama).
- **`ollama`** — the official Ollama container, serving `qwen2.5:7b-instruct` on its standard HTTP API (`:11434`).

There is no internal service mesh beyond `app → ollama`. All other concerns (CV, RAG, aggregation, UI) live as Python modules inside the `app` process. This keeps the dev loop tight for a few-day prototype.

```
                        ┌─────────────────┐
                        │  user's browser │
                        │  (Chrome/FF/..) │
                        └────────┬────────┘
                                 │ HTTP, loopback only
                                 │ 127.0.0.1:8501
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                       app container                            │
│                                                                │
│   ┌───────────┐    ┌──────────────┐    ┌──────────────────┐    │
│   │           │    │   CV module   │   │   aggregator     │    │
│   │ Streamlit ├───▶│  (PyTorch +   ├──▶│  (CV preds →     │    │
│   │    UI     │    │ GT polygons)  │   │  structured JSON)│    │
│   └─────┬─────┘    └──────────────┘    └─────────┬────────┘    │
│         │                                        │             │
│         │                                        ▼             │
│         │                          ┌────────────────────────┐  │
│         │                          │  RAG retriever         │  │
│         │                          │  (ChromaDB +           │  │
│         │                          │   MiniLM embeddings)   │  │
│         │                          └─────────┬──────────────┘  │
│         │                                    │                 │
│         ▼                                    ▼                 │
│   ┌────────────────────────────────────────────────────────┐   │
│   │                  LLM client                            │   │
│   │  (prompt = CV JSON + retrieved docs + section template)│   │
│   └──────────────────────────┬─────────────────────────────┘   │
└──────────────────────────────┼─────────────────────────────────┘
                               │ HTTP :11434
                               ▼
                ┌────────────────────────────┐
                │     ollama container       │
                │  qwen2.5:7b-instruct-q4_K_M│
                └────────────────────────────┘
```

## 2. Components

### 2.1 Streamlit UI (`app/ui/`)

Accessed exclusively via a web browser at `http://localhost:8501` (loopback-bound — see N8). Single-page app with four regions, top to bottom:

1. **Scenario selector** — dropdown over the curated catalog.
2. **Image viewer** — pre/post side-by-side, with the CV overlay toggleable on the post image. A persistent caption beneath the overlay states: *"Building footprints from xView2 reference labels; damage class predicted by ResNet50."* (per F12)
3. **Damage summary** — table with class counts/percentages and total building count.
4. **Report panel** — "Generate Report" button → rendered markdown report with a "sources used" expander listing the retrieved knowledge documents.

Streamlit's built-in caching (`@st.cache_resource` for the CV model and ChromaDB client, `@st.cache_data` for scenario images) is used aggressively to keep interaction snappy.

### 2.2 CV Module (`app/cv/`)

**Architecture:** `torchvision.models.resnet50` with ImageNet-pretrained backbone and a new 4-class classification head. Input is a 6-channel stack (pre RGB + post RGB) on a fixed-size patch.

**Training (one-time, offline; runs inside the `app` container via `scripts/train_classifier.py`):**

1. Iterate xView2 train split. For each labeled building polygon, crop a fixed-size patch (e.g., 128×128 around the bounding box) from both pre and post images. Stack as 6-channel input. Label = damage class from the xView2 JSON.
2. Train the 4-class head (and optionally fine-tune the last block of the backbone) for a few epochs on the RTX 2080 Ti. Expected runtime: ~2–3 h.
3. Save weights to `/data/eo-damage-models/resnet50_damage.pt` (kept outside the repo to avoid bloating it; mirrors the `/data/xView2/` convention).

Invoked as a one-shot job using the same image as the app service:

```sh
docker compose stop ollama                                       # free ~5 GB VRAM
docker compose run --rm app python scripts/train_classifier.py
docker compose start ollama
```

**Inference-time pipeline (in `app/cv/inference.py`):**

1. Load the fine-tuned ResNet50 once, cached via `@st.cache_resource`.
2. Per scenario: load pre+post images and the GT label JSON; extract polygons.
3. Crop the same fixed-size patches as in training; assemble batch.
4. Forward pass → list of `{building_id, polygon, damage_class, confidence}`.

Using ground-truth polygons means we **skip building localization entirely** — a deliberate simplification (see requirements §6).

### 2.3 Aggregator (`app/cv/aggregator.py`)

Pure function: list of building predictions → structured JSON. Schema:

```json
{
  "scenario_id": "hurricane-michael-001",
  "total_buildings": 412,
  "by_class": {
    "no_damage":    {"count": 180, "pct": 43.7},
    "minor_damage": {"count":  92, "pct": 22.3},
    "major_damage": {"count":  78, "pct": 18.9},
    "destroyed":    {"count":  62, "pct": 15.0}
  },
  "spatial": {
    "quadrants": {
      "NW": {"total": 110, "destroyed_pct": 4.5},
      "NE": {"total":  98, "destroyed_pct": 22.4},
      "SW": {"total":  90, "destroyed_pct": 3.3},
      "SE": {"total": 114, "destroyed_pct": 28.1}
    }
  },
  "severity_index": 0.41
}
```

`severity_index` is a single scalar in [0, 1] derived from class weights (e.g., `0*no + 0.33*minor + 0.66*major + 1.0*destroyed`). Used both for UI display and to drive RAG queries.

This structured object is the **single source of truth** that the LLM is allowed to quote when reporting damage figures.

### 2.4 RAG Module (`app/rag/`)

- **`ingest.py`** — one-shot script that reads `knowledge/*.md`, chunks each document (~500-token chunks with overlap), embeds chunks with `sentence-transformers/all-MiniLM-L6-v2`, and writes to a persistent ChromaDB collection in `./chroma/`.
- **`retriever.py`** — query-time module. Takes the structured CV JSON, constructs a natural-language query (e.g., *"hurricane disaster, 15% destroyed buildings, concentrated in east quadrant"*), embeds it, retrieves top-K chunks (K≈5), and returns chunk text + source document name.

Index is built once during image build / first run and persisted as a docker volume.

**Design intent for retrieval behavior:** retrieval is deterministic for a given scenario (same CV outputs → same query → same chunks). The main lever for variety across scenarios is the **disaster type** in the query, which selects the matching per-type knowledge document; cross-cutting documents (damage taxonomy, EO limitations, response prioritization, urban infrastructure risk) are expected to reappear in most queries by design. Within a single disaster type, top-K retrieval will mostly overlap across the 3 scenarios of that type — report-level variation will come from the CV numbers, not from new retrieved chunks.

### 2.5 LLM Client (`app/llm/`)

Thin wrapper around Ollama's HTTP API.

- **Prompt template** (see §6.3) combines: system prompt with grounding rules, retrieved knowledge chunks, the CV JSON, and an explicit section template.
- Generation is non-streaming for v1 (simpler). Streaming is a nice-to-have for the UI.
- Returns markdown text + the list of source documents used (passed through from RAG).

### 2.6 Scenario Catalog (`app/scenarios/catalog.yaml`)

Hand-curated list (3–5 entries) mapping a friendly scenario ID to:

- xView2 event identifier
- specific tile(s) within that event
- a short human-readable description (shown in the UI dropdown)
- expected disaster type (used by the prompt and as a RAG query hint)

```yaml
- id: hurricane-michael-tile-0042
  event: hurricane-michael
  tile: hurricane-michael_00000042
  disaster_type: hurricane
  description: "Hurricane Michael — coastal residential area, severe structural damage"
```

## 3. Data Flow (Happy Path)

```
[User picks scenario in UI]
        │
        ▼
[UI loads pre/post images from /data/xView2]
        │
        ▼
[CV module: load model → crop patches via GT polygons → classify each → list of preds]
        │
        ▼
[Aggregator: preds → structured damage JSON]
        │
        ▼
[UI renders overlay + summary table]
        │
        │  (user clicks "Generate Report")
        ▼
[Retriever: damage JSON → NL query → top-K knowledge chunks]
        │
        ▼
[LLM client: assemble prompt → call ollama → return markdown report]
        │
        ▼
[UI renders report + "sources used" expander]
```

## 4. Container Layout

`docker-compose.yml` (sketch):

```yaml
services:
  app:
    build: .
    ports: ["127.0.0.1:8501:8501"]   # loopback only — no LAN exposure (N8)
    volumes:
      - /data/xView2:/data/xView2:ro
      - /data/eo-damage-models:/data/eo-damage-models   # RW: training writes here
      - ./chroma:/app/chroma
      - ./knowledge:/app/knowledge:ro
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
      - CV_CHECKPOINT_PATH=/data/eo-damage-models/resnet50_damage.pt
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]
    depends_on: [ollama]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

volumes:
  ollama_data:
```

Both containers request the GPU. On 11 GB VRAM, simultaneous occupancy is tight; we keep CV inference and LLM generation serial (the UI flow naturally does this — CV runs on scenario load, LLM runs on button click).

A one-time setup step (documented in README) pulls the LLM model into the ollama volume:

```sh
docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
```

## 5. Directory Structure

```
eo-damage-intelligence-assistant/
├── docker-compose.yml
├── Dockerfile                    # builds the `app` image
├── requirements.txt              # python deps
├── README.md
├── software_requirements.md
├── software_architecture.md
├── scripts/
│   └── train_classifier.py       # one-time fine-tune; writes models/resnet50_damage.pt
├── app/
│   ├── streamlit_app.py          # streamlit entrypoint
│   ├── ui/                       # ui components
│   ├── cv/
│   │   ├── model.py              # ResNet50 + 4-class head; checkpoint loading
│   │   ├── inference.py          # patch extraction + classification
│   │   └── aggregator.py         # damage metrics
│   ├── rag/
│   │   ├── ingest.py             # one-shot indexer
│   │   └── retriever.py          # query-time retrieval
│   ├── llm/
│   │   ├── client.py             # ollama http wrapper
│   │   └── prompts.py            # prompt template + section spec
│   └── scenarios/
│       ├── catalog.yaml          # curated scenarios
│       └── loader.py             # image+label loading from /data/xView2
├── knowledge/                    # markdown docs for RAG (committed)
└── chroma/                       # persisted vector store (gitignored)

# CV checkpoint lives OUTSIDE the repo at:
#   /data/eo-damage-models/resnet50_damage.pt   (produced by scripts/train_classifier.py)
```

## 6. Key Interfaces

### 6.1 CV → Aggregator
List of dicts: `[{building_id: int, polygon: [[x,y], ...], damage_class: str, confidence: float}]`.

### 6.2 Aggregator → RAG/LLM
The structured JSON shown in §2.3 (`scenario_id`, `total_buildings`, `by_class`, `spatial`, `severity_index`).

### 6.3 LLM Prompt Skeleton
```
System: You are an EO disaster-response analyst. Produce a structured assessment
report following the section template exactly. Damage figures MUST come from the
provided JSON. Practice/recommendation claims should be grounded in the provided
knowledge excerpts; if a claim cannot be supported, omit it or mark it uncertain.
Do NOT claim that the system detects or locates buildings — building footprints
are taken from reference labels; only the per-building damage class is predicted.

[KNOWLEDGE EXCERPTS]
<retrieved chunks with source labels>

[DAMAGE DATA]
<aggregator JSON>

[SECTION TEMPLATE]
## Situational Overview
## Damage Breakdown
## Priority Zones
## Uncertainty & Caveats
## Recommended Actions

Write the report now.
```

## 7. Tech Stack & Versions

| Layer       | Tech                                                          | Notes |
|-------------|---------------------------------------------------------------|-------|
| Language    | Python 3.11                                                   | Pinned in Dockerfile |
| UI          | Streamlit ≥ 1.36                                              | |
| CV          | PyTorch 2.x + torchvision                                     | CUDA 12.x base image |
| Embeddings  | `sentence-transformers/all-MiniLM-L6-v2`                      | Small, CPU-friendly |
| Vector DB   | ChromaDB (persistent, local)                                  | No server, embedded mode |
| LLM serving | Ollama (latest image) + `qwen2.5:7b-instruct-q4_K_M`          | |
| Container   | Docker + docker-compose, NVIDIA Container Toolkit             | |

## 8. Configuration & Secrets

- No secrets — the system has no external services at runtime.
- Configuration is via environment variables on the `app` service:
  - `OLLAMA_HOST` (default `http://ollama:11434`)
  - `OLLAMA_MODEL` (default `qwen2.5:7b-instruct-q4_K_M`)
  - `XVIEW2_ROOT` (default `/data/xView2`)
  - `CV_CHECKPOINT_PATH` (default `/data/eo-damage-models/resnet50_damage.pt`)

## 9. Run Instructions (High Level)

1. Extract the xView2 tars under `/data/xView2/` (one-time, outside docker).
2. `docker compose build app` — builds the image used for both training and serving.
3. Train the CV classifier once, **inside the `app` container** (~2–3 h on RTX 2080 Ti):
   ```sh
   docker compose run --rm app python scripts/train_classifier.py
   ```
   Writes `/data/eo-damage-models/resnet50_damage.pt`. Stop `ollama` first if it's running to free GPU memory.
4. Pull the LLM once: `docker compose up -d ollama && docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M`.
5. `docker compose up app`.
6. Open `http://localhost:8501`.
7. On first app run only: the app builds the ChromaDB index from `knowledge/` (~30 s).

## 10. Risks & Open Questions

- **R1 — Classifier quality.** A short fine-tune of ResNet50 on cropped patches may underperform — especially on the `minor_damage` vs `no_damage` boundary, which is hard even for human annotators. Mitigation: oversample minority classes; report per-class accuracy on a held-out split during dev; in the worst case, collapse to a 3-class scheme (`no_damage` / `damaged` / `destroyed`).
- **R2 — VRAM contention.** RTX 2080 Ti has 11 GB. `qwen2.5:7b-q4` (~5 GB) + a ResNet-class CV model (~1–2 GB) should fit comfortably, but we should verify with `nvidia-smi` once both are loaded. If tight, run CV on CPU.
- **R3 — Quality of retrieval.** With only ~10–20 hand-written knowledge docs, retrieval may pull the same 1–2 chunks every time. We will sanity-check this in dev and broaden the corpus if needed.
- **R4 — Streamlit + heavy models.** Streamlit's re-execution model can cause repeated model loading if caching isn't set up correctly. Mitigation: use `@st.cache_resource` for all model/index loading.
- **R5 — xView2 dataset size.** The tars at `/data/xView2/` are not extracted; extraction may consume tens of GB. Confirm disk headroom before unpacking.

## 11. What We Are *Not* Building (Architectural Non-Goals)

- No microservice split for CV / RAG / aggregator — all in-process.
- No message queue, no async workers, no background jobs.
- No REST API exposed to outside clients — Streamlit is the only interface.
- No observability stack (Prometheus/Grafana/etc.). Stdout logs are enough.
- No CI/CD beyond local commits.
