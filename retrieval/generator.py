# retrieval/generator.py
# Supports 3 modes (set GENERATOR_MODE in .env or environment):
#
#   local  (default) — returns top retrieved chunk directly. No API key needed.
#   groq             — uses Groq free API (Llama3). Set GROQ_API_KEY in .env.
#   openai           — uses OpenAI. Set OPENAI_API_KEY in .env.
#
# For a facts-only FAQ chatbot, "local" mode is perfectly adequate
# because the retrieved chunk IS the official factual answer.

import os
from typing import Optional
from dotenv import load_dotenv
from config.settings import LLM_MODEL, LLM_TEMPERATURE, MAX_TOKENS

load_dotenv()

GENERATOR_MODE = os.getenv("GENERATOR_MODE", "local").lower()

# ---------------------------------------------------------------------------
# LOCAL MODE — no LLM, no API key, returns top chunk as the answer
# ---------------------------------------------------------------------------

import re

def _answer_local(system_prompt: str, user_message: str, chunks: list[dict]) -> str:
    """
    Return the most relevant retrieved chunk as the answer.
    No external API call — completely free and offline.
    """
    top = chunks[0]
    text = top.get("text", "").strip()
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if len(lines) >= 3:
        # Document has natural newlines (like tables or bullet points)
        selected = lines[:4]
    else:
        # Solid paragraph: split by periods followed by space (ignores decimals)
        sentences = re.split(r'\.\s+|\.$', text)
        sentences = [s.strip() + "." for s in sentences if s.strip()]
        selected = sentences[:3]
        
    answer = "Based on official documentation:\n\n" + "\n".join(f"- {item}" for item in selected)
    return answer


# ---------------------------------------------------------------------------
# GROQ MODE — free LLM API, OpenAI-compatible, uses Llama3
# ---------------------------------------------------------------------------

_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip3 install openai")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com "
                "and add GROQ_API_KEY=your_key to .env"
            )
        _groq_client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


def _answer_groq(system_prompt: str, user_message: str) -> str:
    client = _get_groq_client()
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    response = client.chat.completions.create(
        model=groq_model,
        temperature=LLM_TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        return "I'm sorry, I was unable to generate an answer for that query. Please try rephrasing it."
    return content.strip()


# ---------------------------------------------------------------------------
# OPENAI MODE
# ---------------------------------------------------------------------------

_openai_client: Optional[object] = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _answer_openai(system_prompt: str, user_message: str) -> str:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------

def generate_answer(
    system_prompt: str,
    user_message:  str,
    top_chunk:     dict,
    all_chunks:    Optional[list] = None,
) -> dict:
    """
    Generate an answer using the configured mode (local / groq / openai).

    Args:
        system_prompt: Facts-only instruction from context_builder.
        user_message:  Assembled context + question from context_builder.
        top_chunk:     Highest-scoring retrieved chunk (for metadata).
        all_chunks:    All retrieved chunks (used by local mode).

    Returns:
        dict: answer, source_url, last_fetched_date
    """
    if GENERATOR_MODE == "local":
        chunks_for_local = all_chunks if all_chunks else [top_chunk]
        answer_text = _answer_local(system_prompt, user_message, chunks_for_local)
    elif GENERATOR_MODE == "groq":
        answer_text = _answer_groq(system_prompt, user_message)
    elif GENERATOR_MODE == "openai":
        answer_text = _answer_openai(system_prompt, user_message)
    else:
        raise ValueError(
            f"Unknown GENERATOR_MODE='{GENERATOR_MODE}'. "
            "Use: local | groq | openai"
        )

    return {
        "answer":            answer_text,
        "source_url":        top_chunk.get("source_url", ""),
        "last_fetched_date": top_chunk.get("last_fetched_date", ""),
        "mode":              GENERATOR_MODE,
    }
