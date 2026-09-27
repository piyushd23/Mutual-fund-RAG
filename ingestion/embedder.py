# ingestion/embedder.py
# Phase 2: Converts chunk texts into 384-dimensional embedding vectors
# using sentence-transformers/all-MiniLM-L6-v2.
# The model is loaded once (lazy singleton) and reused for all calls.

from typing import Optional
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    """
    Lazy-load and cache the embedding model.
    First call downloads the model (~90 MB); subsequent calls reuse it.
    """
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings.

    Args:
        texts: List of raw text strings to embed.

    Returns:
        List of 384-dimensional float vectors (one per input text).
    """
    model = get_model()
    vectors = model.encode(texts, show_progress_bar=True, batch_size=32)
    return vectors.tolist()
