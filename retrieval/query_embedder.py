# retrieval/query_embedder.py
# Phase 3: Embeds a single user query using the SAME model used during ingestion.
# Reusing the singleton from ingestion.embedder ensures the query and corpus
# vectors live in the same vector space.

from ingestion.embedder import get_model


def embed_query(query: str) -> list[float]:
    """
    Embed a single user query string.

    Uses the same all-MiniLM-L6-v2 singleton loaded during ingestion,
    so no second model download occurs.

    Args:
        query: The user's question text.

    Returns:
        A 384-dimensional float vector.
    """
    model = get_model()
    vector = model.encode([query])[0]
    return vector.tolist()
