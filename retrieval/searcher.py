# retrieval/searcher.py
# Phase 3: Queries ChromaDB with a query embedding and returns the Top-K
# most relevant chunks by cosine similarity.

from ingestion.store import get_collection
from config.settings import TOP_K


def search(query_embedding: list[float], top_k: int = TOP_K) -> list[dict]:
    """
    Perform a cosine-similarity search in ChromaDB.

    Args:
        query_embedding: 384-d float vector from query_embedder.embed_query()
        top_k:           Number of results to return (default: settings.TOP_K)

    Returns:
        List of chunk dicts, sorted by descending similarity score, each with:
          text, source_url, document_title, last_fetched_date, score
    """
    collection = get_collection()

    # Guard: if collection is empty, return early
    if collection.count() == 0:
        print("[Searcher] WARNING: ChromaDB collection is empty. Run ingestion first.")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),   # can't request more than stored
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB returns cosine distance (0=identical, 2=opposite)
        # Convert to similarity: similarity = 1 - distance
        similarity = round(1.0 - dist, 4)
        chunks.append({
            "text":             doc,
            "source_url":       meta.get("source_url", ""),
            "document_title":   meta.get("document_title", ""),
            "last_fetched_date": meta.get("last_fetched_date", ""),
            "score":            similarity,
        })

    return chunks
