# config/settings.py
# Central configuration for the MF FAQ RAG Chatbot.
# All tunable constants live here — import from this module everywhere else.

# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
CHROMA_DB_PATH    = "./chroma_db"        # local persistent storage path
CHROMA_COLLECTION = "mf_faq_corpus"     # collection name

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K = 4   # number of chunks to retrieve per query

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
LLM_MODEL       = "gpt-3.5-turbo"   # swap to any OpenAI-compatible model
LLM_TEMPERATURE = 0.1               # low temperature for factual consistency
MAX_TOKENS      = 300               # max answer length in tokens

# ---------------------------------------------------------------------------
# Chunking — token counts (tiktoken cl100k_base encoding)
# ---------------------------------------------------------------------------
# PDFs: SID / KIM / SAI — section-based, larger chunks
PDF_CHUNK_SIZE    = 500
PDF_CHUNK_OVERLAP = 50

# HTML / web pages: FAQs, TER pages — semantic, medium chunks
HTML_CHUNK_SIZE    = 400
HTML_CHUNK_OVERLAP = 40

# Short regulatory circulars (SEBI) — fixed-size, smaller chunks
CIRC_CHUNK_SIZE    = 300
CIRC_CHUNK_OVERLAP = 30
