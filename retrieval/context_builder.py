# retrieval/context_builder.py
# Phase 3: Assembles a structured LLM prompt from the retrieved chunks.
# The system prompt enforces facts-only, no-advice, cite-one-source rules.

# ---------------------------------------------------------------------------
# System prompt — defines the assistant's identity and hard rules
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a highly professional and articulate Mutual Fund FAQ assistant for SBI Mutual Fund.

Rules you must ALWAYS follow:
1. Answer ONLY using information from the provided context. Do not use external knowledge.
2. Structure your answer in a clear, professional way (using paragraphs or bullet points where appropriate) to make it highly readable. Do not arbitrarily restrict your answer length.
3. Keep the tone professional, objective, and helpful.
4. Always cite exactly one source URL from the context (use the exact URL provided).
5. Never give investment advice, make recommendations, or compare fund performance.
6. Never ask the user for personal information.
7. If the context does not contain enough information to answer, respond exactly with:
   "I don't have enough information from official sources to answer this question."
8. End every answer with: Source: <url>
"""

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    """
    Assemble the system prompt and user message for the LLM.

    Args:
        query:  The user's factual question.
        chunks: Top-K retrieved chunk dicts from searcher.search()

    Returns:
        (system_prompt, user_message) — two strings to pass to the LLM.
    """
    # Build context block — number each source for the LLM to reference
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source_url']}]\n{chunk['text']}"
        )
    context_block = "\n\n".join(context_parts)

    user_message = (
        f"Context:\n"
        f"{context_block}\n\n"
        f"Question: {query}\n\n"
        f"Answer (max 3 sentences, end with 'Source: <url>'):"
    )

    return SYSTEM_PROMPT, user_message
