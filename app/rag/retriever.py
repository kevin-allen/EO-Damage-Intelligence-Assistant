"""Query-time RAG retrieval.

Builds a short keyword-bag query from the structured damage metrics
(see architecture §2.4), embeds it with MiniLM, and returns top-K chunks
from the persistent ChromaDB collection.

The query deliberately excludes numerals — numbers belong in the LLM
prompt as source-of-truth context, not in the embedding-space query.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.cv.aggregator import DamageMetrics


SEVERITY_BUCKETS: tuple[tuple[float, str], ...] = (
    (0.25, "minor damage"),
    (0.50, "moderate damage"),
    (0.75, "severe destruction"),
    (1.01, "catastrophic destruction"),
)
FIXED_KEYWORDS = "building damage assessment response priority urban infrastructure"
TOP_K = 5


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source_doc: str
    distance: float


def severity_category(severity_index: float) -> str:
    """Bucket severity_index into a short keyword phrase."""
    for upper, label in SEVERITY_BUCKETS:
        if severity_index < upper:
            return label
    return "catastrophic destruction"


def build_query(metrics: DamageMetrics, disaster_type: str) -> str:
    """Construct the keyword-bag retrieval query."""
    raise NotImplementedError


def retrieve(query: str, k: int = TOP_K, chroma_dir: Path = Path("chroma")) -> list[RetrievedChunk]:
    """Query the persistent ChromaDB collection and return the top-K chunks."""
    raise NotImplementedError
