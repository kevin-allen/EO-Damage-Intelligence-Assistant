# Software Architecture — EO Damage Intelligence Assistant

Status: **draft v0.1** — working strawman to be reviewed/edited collaboratively.

Companion to [`software_requirements.md`](./software_requirements.md). This document describes *how* we will build what that document says we will build.

## 1. Overview

The system is a two-container application with a clean **offline / runtime split**:

- **Offline (one-time, GPU-using)**: a training script fine-tunes ResNet50; a precompute script runs the trained classifier on every catalog scenario and writes JSON files to `predictions/`. Both scripts run inside the `app` Docker image, invoked via `docker compose run --rm --gpus all app ...`.
- **Runtime (per user session, CPU-only on the app side)**: the Streamlit app loads precomputed prediction JSON + scenario imagery + retrieved knowledge chunks, then calls Ollama for report generation. PyTorch is loaded but unused at runtime.

The two containers:

- **`app`** — Streamlit UI, predictions loader, aggregator, RAG retrieval (ChromaDB + sentence-transformers), and the LLM client. No GPU usage at runtime.
- **`ollama`** — the official Ollama container, serving `qwen2.5:7b-instruct` on its HTTP API (`:11434`). Owns the GPU exclusively at runtime.

This split was a deliberate choice: with a fixed 12-scenario catalog, there is no need for live CV inference, and avoiding GPU contention between PyTorch and Ollama makes the demo dramatically more reliable.

### Offline pipeline (one-time)

```
   /data/xView2/   ──────────►  scripts/train_classifier.py  ──►  /data/eo-damage-models/
   (train split)                (inside app image, --gpus all)     resnet50_damage.pt

   /data/xView2/   ──────────►  scripts/precompute_predictions.py  ──►  predictions/
   + catalog.yaml               (inside app image, --gpus all)          <scenario>.json
   + resnet50_damage.pt
```

### Runtime architecture

```
                        ┌─────────────────┐
                        │  user's browser │
                        │  (Chrome/FF/..) │
                        └────────┬────────┘
                                 │ HTTP, loopback only
                                 │ 127.0.0.1:8501
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                  app container  (CPU only at runtime)          │
│                                                                │
│   ┌───────────┐    ┌──────────────────┐    ┌───────────────┐   │
│   │           │    │ predictions      │    │  aggregator   │   │
│   │ Streamlit ├───▶│ loader           ├───▶│ (preds JSON → │   │
│   │    UI     │    │ (reads JSON +    │    │  damage JSON) │   │
│   │           │    │  GT polygons +   │    │               │   │
│   │           │    │  pre/post imgs)  │    │               │   │
│   └─────┬─────┘    └──────────────────┘    └───────┬───────┘   │
│         │                                          │           │
│         │                            ┌─────────────▼─────────┐ │
│         │                            │  RAG retriever        │ │
│         │                            │  (ChromaDB + MiniLM)  │ │
│         │                            └─────────────┬─────────┘ │
│         ▼                                          ▼           │
│   ┌────────────────────────────────────────────────────────┐   │
│   │                  LLM client                            │   │
│   │  (prompt = CV JSON + retrieved docs + section template)│   │
│   └──────────────────────────┬─────────────────────────────┘   │
└──────────────────────────────┼─────────────────────────────────┘
                               │ HTTP :11434
                               ▼
                ┌────────────────────────────┐
                │  ollama container (GPU)    │
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

**Caching:**
- `@st.cache_resource` for the ChromaDB client and the sentence-transformers embedding model (process-wide singletons).
- `@st.cache_data` for per-scenario image loads and per-scenario prediction JSON (keyed on `scenario_id`).

**State management rules** (to avoid Streamlit rerun footguns):
- Derived state lives in `st.session_state`, not recomputed inside widget callbacks.
- Long-running actions (report generation) are triggered by **explicit buttons** (`st.button(...)`), never by widget value changes.
- No widget should implicitly trigger a heavy recomputation. The supported interactions are: pick a scenario, toggle the overlay, click "Generate Report", open/close the "sources used" expander.

### 2.2 CV Module (`app/cv/` + `scripts/`)

**Architecture:** `torchvision.models.resnet50` with ImageNet-pretrained backbone and a new 4-class classification head. Input is a 6-channel stack (pre RGB + post RGB) on a fixed-size 128×128 patch (3-channel ImageNet conv1 is expanded to 6 channels by duplicating the pretrained weights).

**Where it runs:**

| Stage | Path | Where it executes | Frequency |
|---|---|---|---|
| Train | `scripts/train_classifier.py` | `app` image with `--gpus all` | Once |
| Precompute | `scripts/precompute_predictions.py` | `app` image with `--gpus all` | Once per catalog (regen when model or catalog changes) |
| Runtime loader | `app/cv/predictions.py` | `app` container, CPU only | Per UI scenario selection |

**Training (one-time):** iterate xView2 train split → for each labeled building polygon, crop a 128×128 patch from pre and post → stack as 6-channel input → label from xView2 JSON → train the head (and optionally the last backbone block) for a few epochs (~2–3 h on RTX 2080 Ti) → save to `/data/eo-damage-models/resnet50_damage.pt`.

```sh
docker compose stop ollama                                                      # free VRAM
docker compose run --rm --gpus all app python scripts/train_classifier.py
docker compose start ollama
```

**Precompute (one-time per catalog):** for each scenario in `app/scenarios/catalog.yaml`, load pre/post images + GT polygons, crop patches, forward-pass through the trained ResNet50, and write `predictions/<scenario_id>.json` containing `[{building_id, polygon, damage_class, confidence}, ...]`.

```sh
docker compose stop ollama
docker compose run --rm --gpus all app python scripts/precompute_predictions.py
docker compose start ollama
```

**Runtime loader (`app/cv/predictions.py`):** reads `predictions/<scenario_id>.json` from disk and returns the list-of-dicts. No PyTorch operations execute at runtime (PyTorch is imported only because the same image is used for offline jobs). Cached via `@st.cache_data` keyed on `scenario_id`.

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

This structured object is the **single source of truth** for damage figures. Grounding is enforced **technically, not just by instruction** (per F10): a sibling renderer `render_damage_tables(data) -> dict[str, str]` produces deterministic markdown tables (a per-class breakdown and a per-quadrant priority table) directly from the JSON. These pre-rendered strings are inserted verbatim into the final report — the LLM never emits numbers itself.

### 2.4 RAG Module (`app/rag/`)

- **`ingest.py`** — one-shot script that reads `knowledge/*.md`, chunks each document (~500-token chunks with overlap), embeds chunks with `sentence-transformers/all-MiniLM-L6-v2`, and writes to a persistent ChromaDB collection in `./chroma/`.
- **`retriever.py`** — query-time module. Takes the structured CV JSON, constructs a **short keyword-bag query** (not a prose sentence), embeds it with MiniLM, retrieves top-K chunks (K≈5), and returns chunk text + source document name.

  **Query construction:** concatenate tokens from three buckets:
  1. **Disaster type** — one of `hurricane / flood / wildfire / earthquake tsunami`.
  2. **Severity category** — derived from `severity_index`: `< 0.25 → "minor damage"`, `< 0.5 → "moderate damage"`, `< 0.75 → "severe destruction"`, `≥ 0.75 → "catastrophic destruction"`.
  3. **Fixed task keywords** — always: `"building damage assessment response priority urban infrastructure"`.

  Example queries produced (notice no numbers, no prose, just keywords):
  - `"hurricane severe destruction building damage assessment response priority urban infrastructure"`
  - `"flood moderate damage building damage assessment response priority urban infrastructure"`

  Numbers, percentages, and spatial detail are deliberately **excluded from the query** — they belong in the LLM prompt as ground-truth context, not in the embedding-space query. MiniLM retrieves better from keyword-dense short strings than from prose sentences with embedded numerals.

Index is built once during image build / first run and persisted as a docker volume.

**Design intent for retrieval behavior:** retrieval is deterministic for a given scenario (same CV outputs → same query → same chunks). The main lever for variety across scenarios is the **disaster type** in the query, which selects the matching per-type knowledge document; cross-cutting documents (damage taxonomy, EO limitations, response prioritization, urban infrastructure risk) are expected to reappear in most queries by design. Within a single disaster type, top-K retrieval will mostly overlap across the 3 scenarios of that type — report-level variation will come from the CV numbers, not from new retrieved chunks.

### 2.5 LLM Client + Report Assembly (`app/llm/`)

Report generation is **hybrid** (code + LLM), not pure LLM. This is the technical mechanism that backs F10:

1. **Code-rendered tables** — `render_damage_tables(aggregator_json)` produces deterministic markdown for the Damage Breakdown (per-class table) and Priority Zones (per-quadrant table) sections.
2. **LLM prose call** — Ollama is asked to write only the prose sections: Situational Overview, Priority Zones commentary, Uncertainty & Caveats, Recommended Actions. The prompt explicitly forbids restating numbers; the tables are included as reference-only context.
3. **Assembly** — final report is concatenated in fixed section order:
   - `## Situational Overview` ← LLM prose
   - `## Damage Breakdown` ← code-rendered table
   - `## Priority Zones` ← code-rendered table + LLM commentary
   - `## Uncertainty & Caveats` ← LLM prose
   - `## Recommended Actions` ← LLM prose

The LLM client itself is a thin wrapper around Ollama's HTTP API. Generation is non-streaming for v1; streaming is a nice-to-have. The function returns the assembled markdown report + the list of source documents used (passed through from RAG).

### 2.6 Scenario Catalog (`app/scenarios/catalog.yaml`)

Hand-curated list (12 entries — 3 per disaster type) mapping a friendly scenario ID to:

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

## 3. Data Flow

### Offline (one-time setup)

```
[scripts/train_classifier.py]
  /data/xView2/train/
        │
        ▼
  crop patches via GT polygons → fine-tune ResNet50 head
        │
        ▼
  /data/eo-damage-models/resnet50_damage.pt

[scripts/precompute_predictions.py]
  catalog.yaml + /data/xView2/ + resnet50_damage.pt
        │
        ▼  (for each scenario)
  crop patches → classify each building → assemble preds list
        │
        ▼
  predictions/<scenario_id>.json
```

### Runtime (happy path)

```
[User picks scenario in UI]
        │
        ▼
[App loads pre/post images from /data/xView2/  (cached)]
[App loads predictions/<scenario_id>.json       (cached)]
        │
        ▼
[Aggregator: preds JSON → structured damage JSON]
        │
        ▼
[UI renders overlay + summary table]
        │
        │  (user clicks "Generate Report")
        ▼
[Retriever: damage JSON → NL query → top-K knowledge chunks]
        │
        ▼
[LLM client: assemble prompt → HTTP to ollama → return markdown report]
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
      - chroma_data:/app/chroma                         # named volume (not bind-mounted)
      - ./knowledge:/app/knowledge:ro
      - ./predictions:/app/predictions                  # RW: precompute writes here
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
      - CV_CHECKPOINT_PATH=/data/eo-damage-models/resnet50_damage.pt
    depends_on: [ollama]
    # No GPU at runtime — Ollama owns the GPU.
    # Offline jobs (train, precompute) are invoked with --gpus all:
    #   docker compose run --rm --gpus all app python scripts/<job>.py

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
  chroma_data:
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
│   ├── train_classifier.py       # one-time fine-tune; writes resnet50_damage.pt
│   └── precompute_predictions.py # one-shot per scenario; writes predictions/*.json
├── app/
│   ├── streamlit_app.py          # streamlit entrypoint
│   ├── ui/                       # ui components
│   ├── cv/
│   │   ├── model.py              # ResNet50 + 4-class head (shared by scripts/)
│   │   ├── dataset.py            # patch extraction utilities (shared by scripts/)
│   │   ├── predictions.py        # runtime: load predictions/*.json
│   │   └── aggregator.py         # preds → damage metrics
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
└── predictions/                  # precomputed CV outputs (gitignored)
    └── <scenario_id>.json        # produced by scripts/precompute_predictions.py

# Persistent state living OUTSIDE the repo:
#   /data/eo-damage-models/resnet50_damage.pt   — CV checkpoint (scripts/train_classifier.py)
#   docker named volume `chroma_data`           — ChromaDB vector store (built on first app run)
#   docker named volume `ollama_data`           — pulled LLM models
```

## 6. Key Interfaces

### 6.1 CV → Aggregator
List of dicts: `[{building_id: int, polygon: [[x,y], ...], damage_class: str, confidence: float}]`.

### 6.2 Aggregator → RAG/LLM
The structured JSON shown in §2.3 (`scenario_id`, `total_buildings`, `by_class`, `spatial`, `severity_index`).

### 6.3 LLM Prompt Skeleton
```
System: You are an EO disaster-response analyst. Write ONLY the prose sections of
the assessment listed below. Numeric tables (damage breakdown, priority zones) are
pre-rendered by code and inserted by the system — DO NOT restate or modify any
numbers, percentages, or counts. Refer to severity and distribution qualitatively
(e.g., "high concentration in the eastern quadrant", "predominantly minor damage").
Practice/recommendation claims must be grounded in the provided knowledge
excerpts; if a claim cannot be supported, omit it or mark it uncertain.
Do NOT claim that the system detects or locates buildings — footprints come from
reference labels; only the per-building damage class is predicted.

[KNOWLEDGE EXCERPTS]
<retrieved chunks with source labels>

[DAMAGE DATA — REFERENCE ONLY, DO NOT RESTATE]
<aggregator JSON>

[PRE-RENDERED TABLES — REFERENCE ONLY, INSERTED VERBATIM BY THE SYSTEM]
<damage breakdown table>
<priority zones table>

[YOUR OUTPUT — prose sections only, in this exact order]
## Situational Overview
<your prose>

## Priority Zones (commentary)
<your prose interpreting the priority zones table above>

## Uncertainty & Caveats
<your prose>

## Recommended Actions
<your prose>

Write the prose sections now.
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
2. `docker compose build app` — builds the image used for serving and offline jobs.
3. Train the CV classifier (~2–3 h on RTX 2080 Ti):
   ```sh
   docker compose stop ollama
   docker compose run --rm --gpus all app python scripts/train_classifier.py
   ```
   Writes `/data/eo-damage-models/resnet50_damage.pt`.
4. Precompute predictions for every scenario in the catalog:
   ```sh
   docker compose run --rm --gpus all app python scripts/precompute_predictions.py
   ```
   Writes `predictions/<scenario_id>.json`.
5. Pull the LLM into the Ollama volume (one-time):
   ```sh
   docker compose up -d ollama
   docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
   ```
6. `docker compose up app`. (`ollama` already running from step 5.)
7. Open `http://localhost:8501`.
8. On first app run only: the app builds the ChromaDB index from `knowledge/` (~30 s).

## 10. Risks & Open Questions

- **R1 — Classifier quality.** A short fine-tune of ResNet50 on cropped patches may underperform — especially on the `minor_damage` vs `no_damage` boundary, which is hard even for human annotators. Mitigation: oversample minority classes; report per-class accuracy on a held-out split during dev; in the worst case, collapse to a 3-class scheme (`no_damage` / `damaged` / `destroyed`).
- **R2 — VRAM contention (resolved by design).** At runtime the `app` container does not use the GPU — Ollama owns it exclusively. The only times PyTorch touches the GPU are the one-time training and precompute jobs, which require `docker compose stop ollama` first. This was an explicit shift from a live-CV runtime in response to the demo-stability concern.
- **R3 — Quality of retrieval.** With only ~10–20 hand-written knowledge docs, retrieval may pull the same 1–2 chunks every time. We will sanity-check this in dev and broaden the corpus if needed.
- **R4 — Streamlit + heavy models.** Streamlit's re-execution model can cause repeated model loading if caching isn't set up correctly. Mitigation: use `@st.cache_resource` for all model/index loading.
- **R5 — xView2 dataset size.** The tars at `/data/xView2/` are not extracted; extraction may consume tens of GB. Confirm disk headroom before unpacking.

## 11. What We Are *Not* Building (Architectural Non-Goals)

- No microservice split for CV / RAG / aggregator — all in-process.
- No message queue, no async workers, no background jobs.
- No REST API exposed to outside clients — Streamlit is the only interface.
- No observability stack (Prometheus/Grafana/etc.). Stdout logs are enough.
- No CI/CD beyond local commits.
