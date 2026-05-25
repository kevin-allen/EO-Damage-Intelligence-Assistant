"""Query-time RAG retrieval.

Builds a short keyword-bag query from the structured damage metrics
(see architecture §2.4), embeds it with MiniLM, and returns top-K chunks
from the persistent ChromaDB collection.

The query deliberately excludes numerals — numbers belong in the LLM
prompt as source-of-truth context, not in the embedding-space query.

The embedding model and ChromaDB collection are loaded lazily on first
call and cached as module-level singletons (one per process). Streamlit
can wrap the public functions with `@st.cache_resource` if needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from app.cv.aggregator import DamageMetrics
from app.rag.ingest import COLLECTION_NAME, EMBEDDING_MODEL


SEVERITY_BUCKETS: tuple[tuple[float, str], ...] = (
    (0.25, "minor damage"),
    (0.50, "moderate damage"),
    (0.75, "severe destruction"),
    (1.01, "catastrophic destruction"),
)
FIXED_KEYWORDS = "building damage assessment response priority urban infrastructure"
TOP_K = 5

# Map our internal disaster_type slug (catalog form) to the keyword phrase
# embedded into the retrieval query. Spaces, not underscores, so MiniLM
# tokenises each word independently.
DISASTER_QUERY_KEYWORDS: dict[str, str] = {
    "hurricane": "hurricane",
    "wildfire": "wildfire",
    "flood": "flood",
    "earthquake_tsunami": "earthquake tsunami",
}


log = logging.getLogger(__name__)


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
    """Construct the keyword-bag retrieval query (arch §2.4).

    Format: '<disaster keywords> <severity phrase> <fixed task keywords>'.
    Deliberately number-free — numerals are passed to the LLM separately
    as source-of-truth context, not via the embedding-space query.
    """
    disaster_phrase = DISASTER_QUERY_KEYWORDS.get(
        disaster_type, disaster_type.replace("_", " ")
    )
    sev_phrase = severity_category(metrics["severity_index"])
    return f"{disaster_phrase} {sev_phrase} {FIXED_KEYWORDS}"


# --- lazy singletons ---------------------------------------------------------

_embedder: SentenceTransformer | None = None
_collection_cache: dict[tuple[str, str], "chromadb.api.models.Collection.Collection"] = {}


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        log.info(f"loading embedding model {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection(chroma_dir: Path, collection_name: str):
    key = (str(Path(chroma_dir).resolve()), collection_name)
    if key not in _collection_cache:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        _collection_cache[key] = client.get_collection(collection_name)
    return _collection_cache[key]


# --- public API --------------------------------------------------------------

def retrieve(
    query: str,
    k: int = TOP_K,
    chroma_dir: Path = Path("chroma"),
    collection_name: str = COLLECTION_NAME,
) -> list[RetrievedChunk]:
    """Query the persistent ChromaDB collection and return the top-K chunks."""
    embedder = _get_embedder()
    collection = _get_collection(chroma_dir, collection_name)
    query_vec = embedder.encode([query], convert_to_numpy=True).tolist()
    result = collection.query(
        query_embeddings=query_vec,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]
    return [
        RetrievedChunk(
            text=text,
            source_doc=str(meta.get("source_doc", "")),
            distance=float(dist),
        )
        for text, meta, dist in zip(docs, metas, dists)
    ]
