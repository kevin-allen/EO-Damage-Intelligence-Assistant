"""Ollama HTTP client + report assembly.

Per F10 the final report is hybrid: code-rendered tables for numeric
sections, LLM-generated prose for everything else. This module owns the
LLM call and the final concatenation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.cv.aggregator import DamageMetrics
from app.rag.retriever import RetrievedChunk


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
GENERATION_TIMEOUT_S = 120


@dataclass(frozen=True)
class GeneratedReport:
    markdown: str
    sources: list[str]   # knowledge document filenames cited


def call_ollama(prompt: str, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST) -> str:
    """POST to Ollama's /api/generate and return the completion."""
    raise NotImplementedError


def generate_report(
    metrics: DamageMetrics,
    rendered_tables: dict[str, str],
    chunks: list[RetrievedChunk],
    disaster_type: str,
) -> GeneratedReport:
    """Run the hybrid assembly:

    1. Build the prose prompt (with rendered tables as reference only).
    2. Call Ollama for the prose sections.
    3. Concatenate prose + code-rendered tables in fixed section order.
    """
    raise NotImplementedError
