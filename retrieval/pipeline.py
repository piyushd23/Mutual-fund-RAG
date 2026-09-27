# retrieval/pipeline.py
# Phase 3: The single public entry point for the retrieval layer.
# Wires all 5 retrieval steps into one callable: answer(query) -> dict.
#
# Usage from UI or CLI:
#   from retrieval.pipeline import answer
#   result = answer("What is the expense ratio of SBI Blue Chip Fund?")

from retrieval.guardrail       import check_query
from retrieval.query_embedder  import embed_query
from retrieval.searcher        import search
from retrieval.context_builder import build_prompt
from retrieval.generator       import generate_answer


def answer(query: str) -> dict:
    """
    Run the full retrieval pipeline for a user query.

    Pipeline steps:
      1. Guardrail  — reject PII / advice / performance queries immediately
      2. Embed      — convert query to 384-d vector
      3. Search     — retrieve Top-K chunks from ChromaDB
      4. Context    — assemble LLM prompt from retrieved chunks
      5. Generate   — call LLM and get a <=3-sentence factual answer

    Args:
        query: Raw user input string.

    Returns:
        dict with keys:
          allowed (bool)      — True if query passed guardrail
          answer  (str)       — LLM answer (present when allowed=True)
          source_url (str)    — Citation URL (present when allowed=True)
          last_fetched_date (str) — Source freshness date (present when allowed=True)
          message (str)       — Refusal message (present when allowed=False)
    """
    # ---------------------------------------------------------------
    # Step 1: Guardrail — check before any expensive operations
    # ---------------------------------------------------------------
    guard = check_query(query)
    if not guard.allowed:
        return {
            "allowed": False,
            "message": guard.message,
            "reason":  guard.reason,
        }

    # ---------------------------------------------------------------
    # Step 2: Embed the query
    # ---------------------------------------------------------------
    query_embedding = embed_query(query)

    # ---------------------------------------------------------------
    # Step 3: Similarity search in ChromaDB
    # ---------------------------------------------------------------
    chunks = search(query_embedding)

    if not chunks:
        return {
            "allowed":           True,
            "answer":            (
                "I don't have enough information from official sources to answer this. "
                "Please run the ingestion pipeline first."
            ),
            "source_url":        "",
            "last_fetched_date": "",
        }

    # ---------------------------------------------------------------
    # Step 4: Build context + LLM prompt
    # ---------------------------------------------------------------
    system_prompt, user_message = build_prompt(query, chunks)

    # ---------------------------------------------------------------
    # Step 5: Generate answer (local / groq / openai per GENERATOR_MODE)
    # ---------------------------------------------------------------
    result = generate_answer(system_prompt, user_message, chunks[0], all_chunks=chunks)
    result["allowed"] = True
    result["sources"] = [
        {
            "doc_title": c.get("doc_title", "SBI MF Document"),
            "source_url": c.get("source_url", ""),
            "last_fetched_date": c.get("last_fetched_date", ""),
            "preview": c.get("text", "")[:280].strip() + ("..." if len(c.get("text", "")) > 280 else ""),
        }
        for c in chunks
    ]
    return result
