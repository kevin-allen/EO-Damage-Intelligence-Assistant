"""Streamlit entrypoint.

Single-page UI with four regions, top to bottom (arch §2.1):
  1. Scenario selector
  2. Image viewer (pre/post side-by-side, overlay toggleable on post)
  3. Damage summary (per-class + priority-zones tables from the aggregator)
  4. Report panel: Generate Report button -> RAG + Ollama -> hybrid markdown

Loads precomputed predictions from `predictions/*.json` — no live CV
inference at runtime. Run via the container's CMD (`streamlit run
app/streamlit_app.py`) or `docker compose up app`.
"""

from __future__ import annotations

import streamlit as st
from PIL import Image

from app.cv.aggregator import aggregate, render_damage_tables
from app.cv.predictions import BuildingPrediction, load_predictions
from app.llm.client import GeneratedReport, LLMError, generate_report
from app.rag.retriever import RetrievedChunk, build_query, retrieve
from app.scenarios.loader import Scenario, load_catalog, scenario_image_paths
from app.ui.overlay import DAMAGE_COLOR_HEX, render_overlay


IMAGE_SIZE_XY: tuple[int, int] = (1024, 1024)
FOOTPRINT_CAPTION: str = (
    "Building footprints from xView2 reference labels; damage class predicted by ResNet50."
)


@st.cache_resource(show_spinner=False)
def get_catalog() -> list[Scenario]:
    return load_catalog()


def _find_scenario(scenario_id: str) -> Scenario:
    for s in get_catalog():
        if s.id == scenario_id:
            return s
    raise KeyError(scenario_id)


@st.cache_data(show_spinner=False)
def load_pre_post(scenario_id: str) -> tuple[Image.Image, Image.Image]:
    pre_path, post_path, _ = scenario_image_paths(_find_scenario(scenario_id))
    return (
        Image.open(pre_path).convert("RGB"),
        Image.open(post_path).convert("RGB"),
    )


@st.cache_data(show_spinner=False)
def get_predictions(scenario_id: str) -> list[BuildingPrediction]:
    return load_predictions(scenario_id)


@st.cache_data(show_spinner=False)
def get_metrics(scenario_id: str) -> dict:
    return aggregate(scenario_id, get_predictions(scenario_id), IMAGE_SIZE_XY)


@st.cache_data(show_spinner=False)
def get_post_with_overlay(scenario_id: str) -> Image.Image:
    _, post = load_pre_post(scenario_id)
    return render_overlay(post, get_predictions(scenario_id))


def _legend_markdown() -> str:
    items = []
    for cls, hex_color in DAMAGE_COLOR_HEX.items():
        label = cls.replace("_", " ").capitalize()
        items.append(
            f'<span style="display:inline-block;width:10px;height:10px;'
            f'background:{hex_color};border-radius:2px;margin-right:4px;'
            f'vertical-align:middle"></span>{label}'
        )
    return " &nbsp;&nbsp; ".join(items)


def render_scenario_selector() -> str:
    catalog = get_catalog()
    if not catalog:
        st.error("Catalog is empty (app/scenarios/catalog.yaml).")
        st.stop()
    id_to_label = {s.id: f"{s.description}  ·  [{s.id}]" for s in catalog}
    chosen = st.selectbox(
        "Scenario",
        options=[s.id for s in catalog],
        format_func=lambda sid: id_to_label[sid],
        key="scenario_id",
    )
    return chosen


def render_image_viewer(scenario_id: str) -> None:
    pre, post = load_pre_post(scenario_id)
    show_overlay = st.toggle("Show damage overlay on post image", value=True)
    post_display = get_post_with_overlay(scenario_id) if show_overlay else post

    col_pre, col_post = st.columns(2)
    with col_pre:
        st.markdown("**Pre-disaster**")
        st.image(pre, use_container_width=True)
    with col_post:
        st.markdown("**Post-disaster**")
        st.image(post_display, use_container_width=True)
        st.caption(FOOTPRINT_CAPTION)
        if show_overlay:
            st.markdown(_legend_markdown(), unsafe_allow_html=True)


def render_damage_summary(scenario_id: str) -> None:
    metrics = get_metrics(scenario_id)
    tables = render_damage_tables(metrics)

    top_a, top_b, top_c = st.columns(3)
    top_a.metric("Buildings", metrics["total_buildings"])
    top_b.metric("Severity index", f"{metrics['severity_index']:.2f}")
    top_c.metric(
        "Severity bucket",
        _severity_bucket_label(metrics["severity_index"]),
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Damage breakdown**")
        st.markdown(tables["damage_breakdown"])
    with col_b:
        st.markdown("**Priority zones** (mean severity per quadrant)")
        st.markdown(tables["priority_zones"])


def _severity_bucket_label(sev: float) -> str:
    if sev < 0.25:
        return "Minor"
    if sev < 0.50:
        return "Moderate"
    if sev < 0.75:
        return "Severe"
    return "Catastrophic"


def _run_report_pipeline(
    scenario_id: str,
) -> tuple[GeneratedReport, list[RetrievedChunk], str]:
    """Build query, retrieve, generate. Returns (report, chunks, query_str)."""
    scenario = _find_scenario(scenario_id)
    metrics = get_metrics(scenario_id)
    tables = render_damage_tables(metrics)
    query = build_query(metrics, scenario.disaster_type)
    chunks = retrieve(query, k=5)
    report = generate_report(metrics, tables, chunks, scenario.disaster_type)
    return report, chunks, query


def render_report_panel(scenario_id: str) -> None:
    state_key = f"report::{scenario_id}"
    btn_label = "Regenerate Report" if state_key in st.session_state else "Generate Report"
    if st.button(btn_label, type="primary"):
        with st.spinner("Retrieving knowledge + generating prose via Ollama (~30 s on GPU)..."):
            try:
                report, chunks, query = _run_report_pipeline(scenario_id)
            except LLMError as exc:
                st.error(f"Report generation failed: {exc}")
                st.caption(
                    "If Ollama is unreachable, restart with `docker compose up -d ollama`. "
                    "If the model isn't pulled, run "
                    "`docker compose exec ollama ollama pull qwen2.5:14b-instruct-q4_K_M`."
                )
                return
        st.session_state[state_key] = {"report": report, "chunks": chunks, "query": query}

    state = st.session_state.get(state_key)
    if state is None:
        st.caption(
            "Click **Generate Report** to assemble a 5-section structured assessment. "
            "Numeric tables are inserted verbatim from the aggregator; prose is written "
            "by the local LLM grounded in retrieved knowledge documents."
        )
        return

    st.markdown(state["report"].markdown)
    st.caption(FOOTPRINT_CAPTION)

    with st.expander("Sources used"):
        st.caption(f"Retrieval query: `{state['query']}`")
        for c in state["chunks"]:
            preview = c.text.strip().replace("\n", " ")[:200]
            st.markdown(
                f"- **`{c.source_doc}`**  ·  distance={c.distance:.3f}\n\n"
                f"  > {preview}{'...' if len(c.text) > 200 else ''}"
            )


def main() -> None:
    st.set_page_config(
        page_title="EO Damage Intelligence Assistant",
        layout="wide",
    )
    st.title("EO Damage Intelligence Assistant")
    st.caption("Prototype — xView2 satellite imagery + ResNet50 + RAG + Ollama")

    scenario_id = render_scenario_selector()
    scenario = _find_scenario(scenario_id)
    st.markdown(
        f"**{scenario.disaster_type.replace('_', '/').title()}** &middot; "
        f"event `{scenario.event}` &middot; tile `{scenario.tile}`"
    )

    st.divider()
    st.subheader("Imagery + damage overlay")
    render_image_viewer(scenario_id)

    st.divider()
    st.subheader("Damage summary")
    render_damage_summary(scenario_id)

    st.divider()
    st.subheader("Report")
    render_report_panel(scenario_id)


if __name__ == "__main__":
    main()
