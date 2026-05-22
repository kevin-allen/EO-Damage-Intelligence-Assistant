# Software Requirements — EO Damage Intelligence Assistant

Status: **draft v0.1** — working strawman to be reviewed/edited collaboratively.

## 1. Purpose & Goals

Build a local, reproducible prototype that demonstrates how computer vision (CV) outputs from satellite imagery can be transformed into grounded, operational disaster-assessment reports using retrieval-augmented generation (RAG) and a local LLM.

**The primary deliverable is a demo, not a production system.** The goal is to show a credible end-to-end workflow within a few days of work, not to compete with state-of-the-art disaster modeling.

## 2. Target Users & Usage Scenario

- **Primary user:** an EO / disaster-response analyst (simulated) reviewing the impact of a past disaster.
- **Usage scenario:** the user opens the Streamlit UI, selects one of a small set of pre-curated xView2 disaster events, inspects the pre/post satellite imagery and the CV damage predictions, then triggers an LLM-generated assessment report grounded in the CV outputs and a local EO knowledge base.

## 3. Functional Requirements

| ID  | Requirement |
|-----|-------------|
| F1  | The system shall expose a fixed catalog of **12 curated xView2 disaster scenarios**: 3 scenarios for each of 4 disaster types — **hurricane**, **wildfire**, **flood**, **earthquake/tsunami**. Specific tile IDs are chosen by visual inspection during dataset setup. |
| F2  | For each scenario, the UI shall display the **pre-disaster** and **post-disaster** very-high-resolution satellite images side by side. |
| F3  | The system shall run a **ResNet50 building-damage classifier** (ImageNet-pretrained backbone, 4-class classification head fine-tuned once on cropped xView2 building patches) on each scenario, producing per-building damage predictions in 4 classes: `no_damage`, `minor_damage`, `major_damage`, `destroyed`. |
| F4  | The system shall **aggregate** per-building predictions into structured damage metrics: total building count, per-class counts and percentages, and (best-effort) spatial distribution (e.g., per quadrant or per cluster). |
| F5  | The UI shall **visualize CV outputs** as an overlay on the post-disaster image (color-coded per damage class) and as a numeric summary table. |
| F6  | The system shall maintain a **local RAG knowledge base** of ~12 curated markdown documents (300–800 words each) covering: building damage taxonomies, EO imagery limitations and uncertainty, disaster-response prioritization frameworks, urban infrastructure risk, and per-disaster-type guidance (hurricane, wildfire, flood, earthquake/tsunami). Content is hand-written/adapted from public FEMA, USGS, ESA, and xView2 sources. |
| F7  | When the user requests a report, the system shall **retrieve relevant documents** from the RAG store using the structured CV outputs to construct the query. |
| F8  | The system shall call a **local LLM** (`qwen2.5:7b-instruct` via Ollama) to generate a **structured report** with fixed sections (see F9). |
| F9  | Generated reports shall include the following sections: **Situational Overview**, **Damage Breakdown**, **Priority Zones**, **Uncertainty & Caveats**, **Recommended Actions**. |
| F10 | Reports shall be **grounded**: every claim about damage figures must come from the structured CV outputs; every claim about disaster-response practice should be traceable to a retrieved knowledge document. The UI shall surface which knowledge documents were used. |
| F11 | The system shall be **deployable via `docker compose up`** with two services (`app`, `ollama`). |
| F12 | The UI and generated reports shall **transparently state that building footprints are taken from the xView2 reference labels (ground truth)** and that **only the per-building damage class is model-predicted**. The system shall not claim to detect buildings. |
| F13 | The system shall be **accessed exclusively through a web browser** (Chrome/Firefox/Edge) pointed at `http://localhost:8501`. There is no REST API, no CLI, and no programmatic entry point intended for external clients — Streamlit is the only interface. |

## 4. Non-Functional Requirements

| ID  | Requirement |
|-----|-------------|
| N1  | **Reproducibility:** a fresh checkout + `docker compose up` should bring up the full system, assuming the xView2 dataset is mounted from `/data/xView2` and the CV checkpoint exists at `/data/eo-damage-models/resnet50_damage.pt` (mounted into the container at the same path). |
| N2  | **Local execution only:** no external API calls at runtime (no OpenAI, no cloud services). All model inference happens on the workstation. |
| N3  | **Hardware target:** a single workstation with one CUDA GPU (≥ 8 GB VRAM), ≥ 16 GB RAM. Reference: RTX 2080 Ti, 11 GB VRAM, 15 GB RAM. |
| N4  | **Latency budget (soft targets):** scenario load ≤ 5 s, CV inference per scenario ≤ 30 s, report generation ≤ 60 s. Correctness wins over speed. |
| N5  | **Footprint:** disk usage outside the dataset and CV checkpoint should stay under ~10 GB (Ollama model + vector store + image cache). |
| N6  | **Code quality:** Python 3.11, formatted with `ruff` (or `black`), type-annotated public functions. No tests required beyond a smoke test that exercises the end-to-end flow on one scenario. |
| N7  | **Logging:** structured logs at INFO level for each pipeline stage (CV inference start/end, RAG hit list, LLM call). |
| N8  | **Network exposure & auth:** the Streamlit app binds to **`127.0.0.1:8501` only** (loopback). No authentication is implemented; the only protection is the loopback binding. Single-user assumption. |

## 5. In Scope (Summary)

- Streamlit UI with scenario selector, image viewer, CV overlay, report panel.
- Pre-trained xView2 damage classifier (inference only).
- Building-patch extraction using **ground-truth building polygons** from xView2 labels (not predicted).
- Damage aggregation into structured JSON metrics.
- Local ChromaDB vector store seeded from a curated `knowledge/` folder of markdown documents.
- Local Ollama LLM (`qwen2.5:7b-instruct`, Q4_K_M quantization).
- Structured report generation with 5 fixed sections.
- `docker-compose` deployment (`app` + `ollama`).

## 6. Out of Scope (Explicit Non-Goals)

- **Building localization / segmentation.** We use xView2 ground-truth polygons for cropping; the CV model only does classification on those crops.
- **Training or fine-tuning** the CV model. We use a published checkpoint as-is.
- **User-uploaded imagery** or arbitrary areas of interest. Only the curated catalog is supported.
- **Persistence:** no report history, no user accounts, no DB. Each session is ephemeral.
- **Map overlays / geographic visualization** beyond image-space overlays. No Leaflet, no Folium, no real CRS handling.
- **PDF / DOCX export.** Markdown rendered in Streamlit only.
- **Benchmarking** against the xView2 leaderboard. We do not measure or report classifier accuracy in the demo (we may sanity-check it during dev).
- **Multi-user / concurrency.** Single-user prototype.
- **Cloud deployment, Kubernetes, autoscaling, GPU sharing.** Single workstation only.
- **Real-time satellite ingest** or any pipeline beyond the static xView2 dataset.
- **Authentication, secrets management, HTTPS.** Not implemented — access is restricted only by the loopback binding (see N8).
- **REST API, CLI, or any non-browser entry point.** Streamlit UI is the sole interface (see F13).

## 7. Acceptance Criteria ("Demo-Ready" Definition)

The system is considered demo-ready when **all** of the following hold:

1. From a clean clone, `docker compose up` brings up the app and Ollama with no manual steps beyond mounting `/data/xView2` and dropping the CV checkpoint in `models/`.
2. The UI lists 3+ scenarios; selecting any of them shows pre/post imagery within 5 s.
3. CV predictions render as an overlay and a summary table for the selected scenario.
4. Clicking "Generate Report" produces a structured 5-section report within ~60 s, with at least one citation to a retrieved knowledge document.
5. The report's damage numbers match the on-screen summary table (grounding sanity check).
6. The full flow has been exercised end-to-end on at least 3 scenarios without crashes.

## 8. Locked Decisions

These decisions are settled and reflected in the requirements above:

- **D1 — CV model.** We use a **stock ResNet50** (ImageNet-pretrained backbone via `torchvision.models.resnet50`) with a 4-class classification head, fine-tuned once on cropped xView2 building patches. We deliberately do **not** use the official `DIUx-xView/xView2_baseline` repo — a clean ResNet50 with our own minimal training and inference scripts is simpler to build and own. Building patches are cropped using **ground-truth polygons** from the xView2 label JSON (no localization).
- **D2 — Scenarios.** **12 scenarios total**: 3 per disaster type, across hurricane, wildfire, flood, and earthquake/tsunami. Specific tile IDs are picked during dataset setup based on visual quality of the pre/post imagery and density of damaged buildings.
- **D3 — Knowledge corpus.** **~12 markdown documents** in `knowledge/`, 300–800 words each. Hand-written/adapted from public FEMA, USGS, ESA, and xView2 paper sources. Covers: damage taxonomies, EO limitations, response prioritization, urban infrastructure risk, per-disaster-type guidance.
- **D4 — LLM model.** **`qwen2.5:7b-instruct-q4_K_M`** served by Ollama. No automatic fallback; if quality is insufficient after first end-to-end run, model is swapped manually via the `OLLAMA_MODEL` env var.
- **D5 — Imagery framing.** UI and reports refer to "**very-high-resolution satellite imagery**". xView2 imagery is sourced from Maxar's Open Data Program (WorldView-2/3, GeoEye-1) at ~0.3–0.5 m resolution — it is satellite, not aerial.
