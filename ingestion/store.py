# ingestion/store.py
# Phase 2: Persists chunk embeddings and metadata into ChromaDB.
# Uses cosine similarity as the distance metric.

import uuid
import chromadb
from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION


def get_collection() -> chromadb.Collection:
    """
    Open (or create) the persistent ChromaDB collection.
    The database is stored at CHROMA_DB_PATH on disk.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """
    Upsert chunk texts, embeddings, and metadata into ChromaDB.

    Args:
        chunks:     List of chunk dicts from chunker.chunk_document()
        embeddings: Parallel list of embedding vectors from embedder.embed_texts()
    """
    if not chunks:
        print("No chunks to upsert.")
        return

    collection = get_collection()

    ids       = [str(uuid.uuid4()) for _ in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_url":        c["source_url"],
            "document_title":    c["document_title"],
            "page_number":       str(c.get("page_number") or ""),
            "last_fetched_date": c["last_fetched_date"],
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"  [Store] Upserted {len(chunks)} chunks → '{CHROMA_COLLECTION}'")


def collection_count() -> int:
    """Return the total number of documents currently in the collection."""
    return get_collection().count()
