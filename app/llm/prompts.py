"""Prompt template and section ordering for the hybrid report assembly.

See architecture §6.3. The LLM produces only the prose sections; numeric
content is rendered by code (app.cv.aggregator.render_damage_tables) and
inserted into the final report at fixed positions.
"""

from __future__ import annotations

from app.cv.aggregator import DamageMetrics
from app.rag.retriever import RetrievedChunk


SYSTEM_PROMPT = """\
You are an EO disaster-response analyst. Write ONLY the prose sections of
the assessment listed below. Numeric tables (damage breakdown, priority
zones) are pre-rendered by code and inserted into the final report verbatim
by the system - DO NOT restate or modify any numbers, percentages, or
counts. Refer to severity and distribution qualitatively (e.g., "high
concentration in the eastern quadrant", "predominantly minor damage").
Practice and recommendation claims must be grounded in the provided
knowledge excerpts; if a claim cannot be supported, omit it or mark it
uncertain. Do NOT claim that the system detects or locates buildings -
footprints come from reference labels; only the per-building damage class
is predicted.
"""


OUTPUT_TEMPLATE = """\
## Situational Overview
<your prose>

## Priority Zones (commentary)
<your prose interpreting the priority zones table above>

## Uncertainty & Caveats
<your prose>

## Recommended Actions
<your prose>
"""


FINAL_SECTION_ORDER: tuple[str, ...] = (
    "Situational Overview",
    "Damage Breakdown",          # code-rendered
    "Priority Zones",            # code-rendered table + LLM commentary
    "Uncertainty & Caveats",
    "Recommended Actions",
)


def build_prompt(
    metrics: DamageMetrics,
    rendered_tables: dict[str, str],
    chunks: list[RetrievedChunk],
    disaster_type: str,
) -> str:
    """Assemble the full prompt for the LLM prose call."""
    raise NotImplementedError
