"""One-shot ChromaDB indexer for the curated knowledge corpus.

Reads `knowledge/*.md`, chunks each document, embeds chunks with
sentence-transformers/all-MiniLM-L6-v2, and writes to a persistent
ChromaDB collection in /app/chroma (mounted from named volume `chroma_data`).

Re-running rebuilds the collection from scratch; each call is idempotent.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


KNOWLEDGE_DIR = Path("knowledge")
CHROMA_DIR = Path("chroma")
COLLECTION_NAME = "eo_damage_knowledge"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# MiniLM-L6-v2 has a 256-token max context. We chunk to fit, with paragraph-
# level overlap to preserve cross-paragraph context across chunk boundaries.
CHUNK_TOKENS = 256
CHUNK_OVERLAP_PARAGRAPHS = 1


log = logging.getLogger(__name__)


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_markdown(
    text: str,
    tokenizer,
    max_tokens: int = CHUNK_TOKENS,
    overlap_paragraphs: int = CHUNK_OVERLAP_PARAGRAPHS,
) -> list[str]:
    """Split markdown into token-bounded chunks at paragraph boundaries.

    Paragraphs are packed greedily into chunks until adding the next paragraph
    would exceed `max_tokens`. The last `overlap_paragraphs` paragraphs of
    each chunk are repeated at the start of the next chunk to preserve
    cross-boundary context for embedding-space retrieval.

    If a single paragraph exceeds max_tokens, it is split on sentence
    boundaries (". ").
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    def n_tokens(s: str) -> int:
        return len(tokenizer.encode(s, add_special_tokens=False))

    # Expand any paragraph that exceeds the limit into smaller pieces.
    pieces: list[str] = []
    for para in paragraphs:
        if n_tokens(para) <= max_tokens:
            pieces.append(para)
            continue
        sentences = [s.strip() for s in para.split(". ") if s.strip()]
        buf: list[str] = []
        buf_tok = 0
        for sent in sentences:
            st = n_tokens(sent)
            if buf and buf_tok + st > max_tokens:
                pieces.append(". ".join(buf))
                buf, buf_tok = [], 0
            buf.append(sent)
            buf_tok += st
        if buf:
            pieces.append(". ".join(buf))

    chunks: list[str] = []
    current: list[str] = []
    current_tok = 0

    for piece in pieces:
        pt = n_tokens(piece)
        if current and current_tok + pt > max_tokens:
            chunks.append("\n\n".join(current))
            tail = current[-overlap_paragraphs:] if overlap_paragraphs else []
            current = list(tail)
            current_tok = sum(n_tokens(p) for p in current)
            # Shrink overlap if it leaves no room for the next piece.
            while current and current_tok + pt > max_tokens:
                current.pop(0)
                current_tok = sum(n_tokens(p) for p in current)
        current.append(piece)
        current_tok += pt

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def build_index(
    knowledge_dir: Path = KNOWLEDGE_DIR,
    chroma_dir: Path = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """Build the vector index. Returns the number of chunks indexed."""
    knowledge_dir = Path(knowledge_dir)
    chroma_dir = Path(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    docs = sorted(p for p in knowledge_dir.glob("*.md") if p.name.lower() != "readme.md")
    if not docs:
        raise FileNotFoundError(f"no knowledge docs found in {knowledge_dir}")
    log.info(f"loading {len(docs)} knowledge documents from {knowledge_dir}")

    log.info(f"loading embedding model {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    all_texts: list[str] = []
    all_ids: list[str] = []
    all_metas: list[dict] = []
    for doc_path in docs:
        text = doc_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, embedder.tokenizer)
        log.info(f"  {doc_path.name}: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_ids.append(f"{doc_path.name}::{i}")
            all_metas.append({"source_doc": doc_path.name, "chunk_index": i})

    log.info(f"embedding {len(all_texts)} chunks...")
    embeddings = embedder.encode(
        all_texts, show_progress_bar=False, convert_to_numpy=True
    ).tolist()

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        client.delete_collection(name=collection_name)
        log.info(f"deleted existing collection {collection_name!r}")
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        documents=all_texts,
        embeddings=embeddings,
        metadatas=all_metas,
        ids=all_ids,
    )
    log.info(f"indexed {len(all_texts)} chunks into {collection_name!r} at {chroma_dir}")
    return len(all_texts)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    n = build_index()
    print(f"Indexed {n} chunks into {COLLECTION_NAME}")
