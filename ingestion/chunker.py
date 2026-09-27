# ingestion/chunker.py
# Phase 2: Splits raw document text into overlapping token-window chunks.
# Strategy is adaptive — different settings for PDFs, HTML pages, and circulars.

import tiktoken
from config.settings import (
    PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP,
    HTML_CHUNK_SIZE, HTML_CHUNK_OVERLAP,
    CIRC_CHUNK_SIZE, CIRC_CHUNK_OVERLAP,
)

# Use the cl100k_base tokeniser (same as GPT-3.5 / GPT-4 family)
_enc = tiktoken.get_encoding("cl100k_base")

# Keywords that identify short regulatory circulars → smaller chunks
_CIRCULAR_SIGNALS = [
    "sebi.gov.in",
    "circular",
    "aparajitha.com",
]


def _token_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Tokenise `text` and return a list of overlapping text windows.
    Each window is at most `chunk_size` tokens, sliding by (chunk_size - overlap).
    """
    tokens = _enc.encode(text)
    result = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        window = tokens[start:end]
        result.append(_enc.decode(window))
        if end == len(tokens):
            break
        start += chunk_size - overlap
    return result


def _pick_strategy(doc: dict) -> tuple[int, int]:
    """
    Choose (chunk_size, overlap) based on document type and URL signals.
    Priority: PDF > circular signals > HTML default.
    """
    if doc.get("doc_type") == "pdf":
        return PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP

    url = doc.get("source_url", "").lower()
    title = doc.get("document_title", "").lower()
    if any(sig in url or sig in title for sig in _CIRCULAR_SIGNALS):
        return CIRC_CHUNK_SIZE, CIRC_CHUNK_OVERLAP

    return HTML_CHUNK_SIZE, HTML_CHUNK_OVERLAP


def chunk_document(doc: dict) -> list[dict]:
    """
    Chunk a single loaded document dict into smaller pieces.

    Args:
        doc: Output dict from loader.load_source()

    Returns:
        List of chunk dicts, each with:
          text, source_url, document_title, page_number,
          last_fetched_date, chunk_index
    """
    chunk_size, overlap = _pick_strategy(doc)
    raw_chunks = _token_split(doc["text"], chunk_size, overlap)

    chunks = []
    for i, text in enumerate(raw_chunks):
        if text.strip():
            chunks.append({
                "text": text,
                "source_url": doc["source_url"],
                "document_title": doc["document_title"],
                "page_number": doc.get("page_number"),
                "last_fetched_date": doc["last_fetched_date"],
                "chunk_index": i,
            })

    return chunks
