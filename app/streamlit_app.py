"""Streamlit entrypoint.

Single-page UI with four regions: scenario selector, image viewer (with
CV overlay), damage summary, and report panel. Loads precomputed predictions
from `predictions/*.json` (no live CV inference at runtime).

Run via the container's CMD: `streamlit run app/streamlit_app.py`.
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="EO Damage Intelligence Assistant", layout="wide")
    st.title("EO Damage Intelligence Assistant")
    st.caption("Prototype — xView2 satellite imagery + ResNet50 + RAG + Ollama")
    st.info("Skeleton only — UI not implemented yet.")


if __name__ == "__main__":
    main()
