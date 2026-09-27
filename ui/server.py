# ui/server.py
# High-performance FastAPI server for SBI Mutual Fund FAQ RAG Assistant.
# Replaces Streamlit with a modern, lightweight, production-ready web application
# that is easy to deploy on Docker, Render, Railway, AWS, or Hugging Face.

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure root folder is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from retrieval.pipeline import answer
from ingestion.store import collection_count

app = FastAPI(
    title="SBI Mutual Fund FAQ Assistant",
    description="Factual RAG Assistant for SBI Mutual Fund, SEBI & AMFI FAQs",
    version="1.0.0",
)

# Enable CORS for easy cross-origin integration or embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatRequest(BaseModel):
    query: str


@app.get("/api/health")
def health():
    """Healthcheck endpoint for orchestrators (Docker, Kubernetes, Render)."""
    return {"status": "ok", "service": "sbi-mf-rag-assistant"}


@app.get("/api/stats")
def get_stats():
    """Returns knowledge base stats, active model mode, and corpus info."""
    try:
        count = collection_count()
    except Exception as e:
        count = 0

    mode = os.getenv("GENERATOR_MODE", "local").lower()
    mode_display = {
        "local": "Local Offline (No API Key)",
        "groq": "Groq Llama-3 (Cloud LLM)",
        "openai": "OpenAI GPT (Cloud LLM)",
    }.get(mode, mode.title())

    return {
        "status": "online",
        "chunks_count": count,
        "generator_mode": mode,
        "generator_display": mode_display,
        "embedding_model": "all-MiniLM-L6-v2 (384 dims)",
        "vector_store": "ChromaDB (Persistent)",
        "corpus_name": "SBI Mutual Fund Official Docs",
        "guardrail_status": "Active (PII & Advice Filter)",
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Processes user question through the RAG pipeline."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        result = answer(query)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "allowed": False,
                "error": True,
                "message": f"An error occurred while processing your query: {str(e)}",
            },
        )


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serve the single-page application UI."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "UI frontend index.html not found"},
        )
    return FileResponse(index_file)
