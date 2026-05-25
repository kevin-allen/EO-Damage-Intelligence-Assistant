"""Prompt template and section ordering for the hybrid report assembly.

See architecture §6.3. The LLM produces only the prose sections; numeric
content is rendered by code (app.cv.aggregator.render_damage_tables) and
inserted into the final report at fixed positions.
"""

from __future__ import annotations

import json

from app.cv.aggregator import DamageMetrics
from app.rag.retriever import RetrievedChunk


SYSTEM_PROMPT = """\
You are an EO disaster-response analyst writing the four prose sections of
a structured assessment. Follow these rules strictly:

1. NO NUMBERS IN YOUR OUTPUT. Do not include any digits (0-9), percentages,
   counts, ratios, fractions, or numerical written-out values ("one
   building", "several hundred", "two-thirds") in any of the four prose
   sections. The numeric tables are inserted by the system separately - do
   not preview, restate, summarize, or paraphrase the table numbers in your
   prose. Describe severity and distribution ONLY in qualitative words:
   "predominantly major damage", "concentrated in the northwest quadrant",
   "a small number of intact structures", "uniformly severe across the
   tile". Words like "most", "few", "many", "concentrated", "uniform",
   "evenly distributed" are encouraged; anything quantitative is forbidden.

2. DO NOT INVENT SCENARIO-SPECIFIC FACTS. Do not state a storm category,
   wind speed, intensity rating, named event, named location (city, state,
   country), specific date, building type, casualty count, or any other
   specific that is not present in the structured damage data provided.
   The knowledge excerpts are background reference for general practices
   only - do NOT lift specific facts (storm names, categories, historical
   examples) from them as if they describe this scenario.

3. GROUND PRACTICE CLAIMS. Recommendations and response-practice claims
   must be supportable from the knowledge excerpts. If a claim cannot be
   supported, omit it or mark it explicitly uncertain.

4. NO BUILDING-DETECTION CLAIMS. Building footprints come from reference
   labels; only the per-building damage class is predicted. Do not claim
   the system detects, locates, identifies, or finds buildings.

Output the four sections in the exact order and with the exact headers
shown in the template. No preamble, no closing remarks, no commentary
outside the four sections.
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


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no knowledge excerpts were retrieved)"
    blocks = []
    for c in chunks:
        blocks.append(f"--- {c.source_doc} ---\n{c.text.strip()}")
    return "\n\n".join(blocks)


def build_prompt(
    metrics: DamageMetrics,
    rendered_tables: dict[str, str],
    chunks: list[RetrievedChunk],
    disaster_type: str,
) -> str:
    """Assemble the full prompt for the LLM prose call (user message body).

    The system prompt is sent separately via the chat API. This function
    builds the user message — knowledge excerpts, structured damage data,
    pre-rendered tables, and the output template.
    """
    return f"""\
Disaster type: {disaster_type.replace('_', '/')}

[KNOWLEDGE EXCERPTS]
{_format_chunks(chunks)}

[DAMAGE DATA - REFERENCE ONLY, DO NOT RESTATE THE NUMBERS]
{json.dumps(metrics, indent=2)}

[PRE-RENDERED TABLES - REFERENCE ONLY, INSERTED VERBATIM BY THE SYSTEM]

Damage breakdown:
{rendered_tables['damage_breakdown']}

Priority zones (sorted by mean severity):
{rendered_tables['priority_zones']}

[YOUR OUTPUT - prose sections only, in this exact order]
{OUTPUT_TEMPLATE}
Write the prose sections now."""
