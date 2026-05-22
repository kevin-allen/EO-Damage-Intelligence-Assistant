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
| F3  | The system shall use a **ResNet50 building-damage classifier** (ImageNet-pretrained backbone, 4-class classification head fine-tuned once on cropped xView2 building patches) to produce per-building damage predictions in 4 classes: `no_damage`, `minor_damage`, `major_damage`, `destroyed`. |
| F3a | **Predictions are precomputed offline**, once per scenario, via `scripts/precompute_predictions.py`. The script reads each scenario from the catalog, crops patches via GT polygons, runs the classifier, and writes `predictions/<scenario_id>.json`. The Streamlit app loads these precomputed JSON files at runtime; **no live CV inference occurs during user interaction**. |
| F4  | The system shall **aggregate** per-building predictions into structured damage metrics: total building count, per-class counts and percentages, and (best-effort) spatial distribution (e.g., per quadrant or per cluster). |
| F5  | The UI shall **visualize CV outputs** as an overlay on the post-disaster image (color-coded per damage class) and as a numeric summary table. |
| F6  | The system shall maintain a **local RAG knowledge base** of ~12 curated markdown documents (300–800 words each) covering: building damage taxonomies, EO imagery limitations and uncertainty, disaster-response prioritization frameworks, urban infrastructure risk, and per-disaster-type guidance (hurricane, wildfire, flood, earthquake/tsunami). Content is hand-written/adapted from public FEMA, USGS, ESA, and xView2 sources. |
| F7  | When the user requests a report, the system shall **retrieve relevant documents** from the RAG store using the structured CV outputs to construct the query. |
| F8  | The system shall call a **local LLM** (`qwen2.5:7b-instruct` via Ollama) to generate a **structured report** with fixed sections (see F9). |
| F9  | Generated reports shall include the following sections: **Situational Overview**, **Damage Breakdown**, **Priority Zones**, **Uncertainty & Caveats**, **Recommended Actions**. |
| F10 | Reports shall be **technically grounded**, not just instructed-to-be-grounded: (a) all numeric figures (counts, percentages, severity index) are produced by **code-rendered markdown tables** built directly from the aggregator JSON — the LLM does not emit numbers; (b) the LLM produces only the **prose sections** (Situational Overview, Priority Zones commentary, Uncertainty & Caveats, Recommended Actions), grounded in retrieved knowledge chunks; (c) the final report is assembled by concatenating the code-rendered tables and the LLM prose in the fixed section order; (d) the UI shall surface which knowledge documents were used. |
| F11 | The system shall be **deployable via `docker compose up`** with two services (`app`, `ollama`). |
| F12 | The UI and generated reports shall **transparently state that building footprints are taken from the xView2 reference labels (ground truth)** and that **only the per-building damage class is model-predicted**. The system shall not claim to detect buildings. |
| F13 | The system shall be **accessed exclusively through a web browser** (Chrome/Firefox/Edge) pointed at `http://localhost:8501`. There is no REST API, no CLI, and no programmatic entry point intended for external clients — Streamlit is the only interface. |

## 4. Non-Functional Requirements

| ID  | Requirement |
|-----|-------------|
| N1  | **Reproducibility:** after the documented one-time setup — (a) xView2 tars extracted under `/data/xView2/`, (b) `app` image built (`docker compose build app`), (c) ResNet50 trained to `/data/eo-damage-models/resnet50_damage.pt`, (d) predictions precomputed under `predictions/`, (e) `qwen2.5:7b-instruct-q4_K_M` pulled into the Ollama volume — the system runs via `docker compose up app`. The setup steps are documented and themselves containerized (training and precompute run inside the `app` image). |
| N2  | **Local execution only:** no external API calls at runtime (no OpenAI, no cloud services). All model inference happens on the workstation. |
| N3  | **Hardware target:** a single workstation with one CUDA GPU (≥ 8 GB VRAM), ≥ 16 GB RAM. Reference: RTX 2080 Ti, 11 GB VRAM, 15 GB RAM. |
| N4  | **Latency budget (soft targets):** scenario selection → image + predictions rendered ≤ 2 s (loading precomputed JSON + image from disk); report generation ≤ 60 s (Ollama-bound). Correctness wins over speed. |
| N5  | **Footprint:** disk usage outside the dataset and CV checkpoint should stay under ~10 GB (Ollama model + vector store + image cache). |
| N6  | **Code quality:** Python 3.11, formatted with `ruff` (or `black`), type-annotated public functions. No tests required beyond a smoke test that exercises the end-to-end flow on one scenario. |
| N7  | **Logging:** structured logs at INFO level for each pipeline stage. Offline jobs log training epoch metrics and per-scenario precompute progress. Runtime app logs scenario load, predictions load, RAG hit list, and LLM call timings. |
| N8  | **Network exposure & auth:** the Streamlit app binds to **`127.0.0.1:8501` only** (loopback). No authentication is implemented; the only protection is the loopback binding. Single-user assumption. |

## 5. In Scope (Summary)

- Streamlit UI with scenario selector, image viewer, CV overlay, report panel.
- ResNet50 damage classifier fine-tuned once on cropped xView2 patches (offline-only — no live inference at runtime).
- Offline precompute step that runs the classifier on every catalog scenario and writes `predictions/<scenario_id>.json` consumed by the app.
- Building-patch extraction using **ground-truth building polygons** from xView2 labels (not predicted).
- Damage aggregation (preds JSON → structured metrics) at runtime.
- Local ChromaDB vector store seeded from a curated `knowledge/` folder of markdown documents.
- Local Ollama LLM (`qwen2.5:7b-instruct`, Q4_K_M quantization).
- Structured report generation with 5 fixed sections.
- `docker-compose` deployment (`app` + `ollama`).

## 6. Out of Scope (Explicit Non-Goals)

- **Building localization / segmentation.** We use xView2 ground-truth polygons for cropping; the CV model only does classification on those crops.
- **Live CV inference at runtime.** Predictions are precomputed offline once per scenario; the app loads precomputed JSON. PyTorch is an offline-only dependency.
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

1. After completing the documented one-time setup (dataset extraction, image build, training, precompute, model pull), `docker compose up app` brings up the Streamlit app with no further manual steps.
2. The UI lists all 12 curated scenarios; selecting any of them shows pre/post imagery and the precomputed CV overlay within ~2 s.
3. CV predictions render as an overlay and a summary table for the selected scenario (loaded from `predictions/<scenario_id>.json`).
4. Clicking "Generate Report" produces a structured 5-section report within ~60 s, with at least one citation to a retrieved knowledge document.
5. The report's damage numbers match the on-screen summary table (grounding sanity check).
6. The full flow (select → view overlay → generate report) has been exercised end-to-end on **all 12 scenarios**, without crashes. Each disaster type (hurricane, wildfire, flood, earthquake/tsunami) has at least one scenario whose generated report has been manually spot-checked for grounding (numbers match the summary table; cited knowledge docs are topically relevant).

## 8. Locked Decisions

These decisions are settled and reflected in the requirements above:

- **D1 — CV model.** We use a **stock ResNet50** (ImageNet-pretrained backbone via `torchvision.models.resnet50`) with a 4-class classification head, fine-tuned once on cropped xView2 building patches. We deliberately do **not** use the official `DIUx-xView/xView2_baseline` repo — a clean ResNet50 with our own minimal training and inference scripts is simpler to build and own. Building patches are cropped using **ground-truth polygons** from the xView2 label JSON (no localization).
- **D2 — Scenarios.** **12 scenarios total**: 3 per disaster type, across hurricane, wildfire, flood, and earthquake/tsunami. Specific tile IDs are picked during dataset setup based on visual quality of the pre/post imagery and density of damaged buildings.
- **D3 — Knowledge corpus.** **~12 markdown documents** in `knowledge/`, 300–800 words each. Hand-written/adapted from public FEMA, USGS, ESA, and xView2 paper sources. Covers: damage taxonomies, EO limitations, response prioritization, urban infrastructure risk, per-disaster-type guidance.
- **D4 — LLM model.** **`qwen2.5:7b-instruct-q4_K_M`** served by Ollama. No automatic fallback; if quality is insufficient after first end-to-end run, model is swapped manually via the `OLLAMA_MODEL` env var.
- **D5 — Imagery framing.** UI and reports refer to "**very-high-resolution satellite imagery**". xView2 imagery is sourced from Maxar's Open Data Program (WorldView-2/3, GeoEye-1) at ~0.3–0.5 m resolution — it is satellite, not aerial.
