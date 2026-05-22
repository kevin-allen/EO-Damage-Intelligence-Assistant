"""One-shot ChromaDB indexer for the curated knowledge corpus.

Reads `knowledge/*.md`, chunks each document, embeds chunks with
sentence-transformers/all-MiniLM-L6-v2, and writes to a persistent
ChromaDB collection in /app/chroma (mounted from named volume `chroma_data`).

Intended to be run once during first app startup; the resulting index is
reused across sessions.
"""

from __future__ import annotations

from pathlib import Path


KNOWLEDGE_DIR = Path("knowledge")
CHROMA_DIR = Path("chroma")
COLLECTION_NAME = "eo_damage_knowledge"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50


def build_index(
    knowledge_dir: Path = KNOWLEDGE_DIR,
    chroma_dir: Path = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """Build the vector index. Returns the number of chunks indexed."""
    raise NotImplementedError


def chunk_markdown(text: str, max_tokens: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split a markdown document into overlapping ~500-token chunks."""
    raise NotImplementedError


if __name__ == "__main__":
    n = build_index()
    print(f"Indexed {n} chunks into {COLLECTION_NAME}")
