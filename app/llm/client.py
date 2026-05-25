"""Ollama HTTP client + hybrid report assembly.

Per F10 the final report is hybrid: code-rendered tables for numeric
sections, LLM-generated prose for everything else. This module owns the
LLM call and the final concatenation.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import requests

from app.cv.aggregator import DamageMetrics
from app.llm.prompts import (
    FINAL_SECTION_ORDER,
    SYSTEM_PROMPT,
    build_prompt,
)
from app.rag.retriever import RetrievedChunk


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
GENERATION_TIMEOUT_S = 120
GENERATION_TEMPERATURE = 0.2


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedReport:
    markdown: str
    sources: list[str]   # knowledge document filenames cited (deduped, in order)


class LLMError(RuntimeError):
    """Raised when Ollama is unreachable or returns an error."""


def call_ollama(
    user_prompt: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = OLLAMA_MODEL,
    host: str = OLLAMA_HOST,
    temperature: float = GENERATION_TEMPERATURE,
    timeout: float = GENERATION_TIMEOUT_S,
) -> str:
    """POST to Ollama's /api/chat and return the assistant message content.

    Non-streaming. Raises LLMError on transport or HTTP error.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    url = f"{host.rstrip('/')}/api/chat"
    log.info(f"calling ollama: model={model} prompt_chars={len(user_prompt)}")
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"ollama unreachable at {host}: {exc}") from exc
    if resp.status_code != 200:
        raise LLMError(f"ollama returned HTTP {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    msg = body.get("message") or {}
    content = msg.get("content", "")
    if not content:
        raise LLMError(f"ollama returned empty content; full body: {str(body)[:300]}")
    log.info(f"ollama completed: output_chars={len(content)}")
    return content


_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", flags=re.DOTALL | re.IGNORECASE)
_DIGIT_RE = re.compile(r"\d")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _strip_reasoning(text: str) -> str:
    """Strip <think>...</think> reasoning blocks emitted by R1-family models."""
    return _THINK_BLOCK.sub("", text)


def _scrub_prose(text: str) -> str:
    """F10 post-generation guardrail: drop any sentence containing a digit.

    Numerical content belongs only in the code-rendered tables that are
    inserted verbatim by the assembler. The LLM is instructed to write
    qualitatively; this is the mechanical backstop when it drifts (storm
    categories, percentage restatements, historical years, etc.).

    Preserves paragraph structure: scrubs sentence-by-sentence within each
    paragraph and drops a paragraph entirely if all its sentences had digits.
    """
    if not text:
        return text
    paragraphs = text.split("\n\n")
    out_paragraphs: list[str] = []
    for para in paragraphs:
        sentences = _SENTENCE_SPLIT.split(para)
        kept = [s for s in sentences if s and not _DIGIT_RE.search(s)]
        if kept:
            out_paragraphs.append(" ".join(kept))
    return "\n\n".join(out_paragraphs)


def _parse_sections(text: str) -> dict[str, str]:
    """Split a markdown blob into {header: body} keyed on '## ' headers."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = stripped[3:].strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _pick(prose: dict[str, str], *candidates: str) -> str:
    """Return the first non-empty prose body matching any candidate header."""
    for key in candidates:
        if key in prose and prose[key].strip():
            return prose[key].strip()
    # case-insensitive fallback
    lower = {k.lower(): v for k, v in prose.items()}
    for key in candidates:
        v = lower.get(key.lower(), "").strip()
        if v:
            return v
    return ""


def _assemble_markdown(
    prose: dict[str, str],
    rendered_tables: dict[str, str],
) -> str:
    parts: list[str] = []
    for section in FINAL_SECTION_ORDER:
        if section == "Damage Breakdown":
            parts.append("## Damage Breakdown\n\n" + rendered_tables["damage_breakdown"])
        elif section == "Priority Zones":
            commentary = _scrub_prose(_pick(prose, "Priority Zones (commentary)", "Priority Zones"))
            block = "## Priority Zones\n\n" + rendered_tables["priority_zones"]
            if commentary:
                block += "\n\n" + commentary
            parts.append(block)
        else:
            body = _scrub_prose(_pick(prose, section))
            parts.append(f"## {section}\n\n" + (body or "_(no prose returned)_"))
    return "\n\n".join(parts)


def _unique_sources(chunks: list[RetrievedChunk]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for c in chunks:
        if c.source_doc and c.source_doc not in seen:
            seen.add(c.source_doc)
            ordered.append(c.source_doc)
    return ordered


def generate_report(
    metrics: DamageMetrics,
    rendered_tables: dict[str, str],
    chunks: list[RetrievedChunk],
    disaster_type: str,
) -> GeneratedReport:
    """Run the hybrid assembly:

    1. Build the user prompt (knowledge excerpts + metrics JSON + tables).
    2. Call Ollama for the prose sections.
    3. Concatenate prose + code-rendered tables in fixed section order.

    Returns the final markdown and the list of source documents used.
    """
    user_prompt = build_prompt(metrics, rendered_tables, chunks, disaster_type)
    raw_prose = call_ollama(user_prompt)
    cleaned = _strip_reasoning(raw_prose)
    prose = _parse_sections(cleaned)
    markdown = _assemble_markdown(prose, rendered_tables)
    return GeneratedReport(markdown=markdown, sources=_unique_sources(chunks))
