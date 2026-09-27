# scripts/inspect_pipeline.py
# Inspection script — runs a MINI ingestion on 2 sample URLs,
# then writes chunks.txt (text chunks) and embeddings.txt (vectors)
# to the data/ folder so you can inspect them.
#
# Also checks if ChromaDB is populated and reports the count.
#
# Usage:
#   python3 scripts/inspect_pipeline.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingestion.loader   import load_source
from ingestion.chunker  import chunk_document
from ingestion.embedder import embed_texts
from ingestion.store    import upsert_chunks, collection_count

# Use 2 small public HTML pages for a fast inspection run
SAMPLE_URLS = [
    "https://www.sbimf.com/faq",
    "https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def run():
    print("=" * 60)
    print("Inspection Run (2 sample URLs)")
    print("=" * 60)

    all_chunks = []
    for url in SAMPLE_URLS:
        print(f"\nLoading: {url}")
        try:
            docs = load_source(url)
            for doc in docs:
                chunks = chunk_document(doc)
                all_chunks.extend(chunks)
                print(f"  → {len(chunks)} chunks from '{doc['document_title'][:60]}'")
        except Exception as e:
            print(f"  ERROR: {e}")

    if not all_chunks:
        print("No chunks produced. Check your internet connection.")
        return

    print(f"\nTotal chunks: {len(all_chunks)}")

    # ------------------------------------------------------------------
    # Write chunks.txt — human-readable chunk dump
    # ------------------------------------------------------------------
    chunks_path = os.path.join(DATA_DIR, "chunks.txt")
    with open(chunks_path, "w", encoding="utf-8") as f:
        f.write(f"CHUNK INSPECTION — {len(all_chunks)} chunks from {len(SAMPLE_URLS)} sample URLs\n")
        f.write("=" * 80 + "\n\n")
        for i, chunk in enumerate(all_chunks, 1):
            f.write(f"--- CHUNK {i} ---\n")
            f.write(f"Source URL   : {chunk['source_url']}\n")
            f.write(f"Doc Title    : {chunk['document_title']}\n")
            f.write(f"Page No      : {chunk.get('page_number', 'N/A')}\n")
            f.write(f"Fetched Date : {chunk['last_fetched_date']}\n")
            f.write(f"Chunk Index  : {chunk['chunk_index']}\n")
            f.write(f"Text ({len(chunk['text'])} chars):\n")
            f.write(chunk["text"][:800])   # show first 800 chars
            if len(chunk["text"]) > 800:
                f.write(f"\n... [truncated, {len(chunk['text']) - 800} more chars]")
            f.write("\n\n")
    print(f"\n✅ Chunks written → {chunks_path}")

    # ------------------------------------------------------------------
    # Embed chunks
    # ------------------------------------------------------------------
    print("Embedding chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)

    # ------------------------------------------------------------------
    # Write embeddings.txt — vector dump (first 10 dims shown per chunk)
    # ------------------------------------------------------------------
    emb_path = os.path.join(DATA_DIR, "embeddings.txt")
    with open(emb_path, "w", encoding="utf-8") as f:
        f.write(f"EMBEDDING INSPECTION — {len(embeddings)} vectors ({len(embeddings[0])}-d each)\n")
        f.write("=" * 80 + "\n\n")
        for i, (chunk, vec) in enumerate(zip(all_chunks, embeddings), 1):
            f.write(f"--- EMBEDDING {i} ---\n")
            f.write(f"Source : {chunk['source_url']}\n")
            f.write(f"Title  : {chunk['document_title'][:60]}\n")
            f.write(f"Dims   : {len(vec)}\n")
            # Show first 16 and last 4 dimensions
            preview = [f"{v:.6f}" for v in vec[:16]]
            tail    = [f"{v:.6f}" for v in vec[-4:]]
            f.write(f"Vector : [{', '.join(preview)}, ..., {', '.join(tail)}]\n")
            # Min / max / mean
            f.write(f"Stats  : min={min(vec):.4f}  max={max(vec):.4f}  mean={sum(vec)/len(vec):.4f}\n\n")
    print(f"✅ Embeddings written → {emb_path}")

    # ------------------------------------------------------------------
    # Store in ChromaDB and report
    # ------------------------------------------------------------------
    print("Storing in ChromaDB...")
    upsert_chunks(all_chunks, embeddings)
    count = collection_count()

    print(f"\n✅ ChromaDB count after upsert: {count} chunks")
    print(f"   DB path: ./chroma_db  (persistent on disk)")
    print("\nChromaDB IS persistent — data survives process restarts.")
    print("Re-running run_ingestion.py adds more chunks to the same DB.")
    print("=" * 60)
    print("Inspect the output files:")
    print(f"  data/chunks.txt     — human-readable text chunks")
    print(f"  data/embeddings.txt — 384-d embedding vectors")
    print(f"  ./chroma_db/        — ChromaDB on-disk storage")

if __name__ == "__main__":
    run()
