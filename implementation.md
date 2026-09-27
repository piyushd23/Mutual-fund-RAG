# Implementation Guide
## Mutual Fund FAQ RAG Chatbot — Phase-wise Plan

| Field | Detail |
|---|---|
| **Reference** | [architecture.md](./architecture.md) · [PRD.md](./PRD.md) |
| **Version** | 1.0 |
| **Date** | 2026-09-27 |

---

## Overview

The implementation is broken into **5 phases**, each self-contained and independently testable. Complete and verify each phase before moving to the next.

```
Phase 1: Project Setup & Environment
Phase 2: Data Ingestion Pipeline  (Loader → Chunker → Embedder → ChromaDB)
Phase 3: Retrieval Pipeline       (Guardrail → Search → Context → LLM)
Phase 4: UI Layer                 (Streamlit app)
Phase 5: Polish & Deliverables    (QA, README, Sample Q&A, Disclaimer)
```

---

## Phase 1 — Project Setup & Environment

**Goal:** Get a clean, reproducible project skeleton running locally.

### 1.1 Create Project Structure

```bash
mkdir -p RAG_Chatbot/{ingestion,retrieval,ui,data,config,tests}
touch RAG_Chatbot/ingestion/{__init__.py,loader.py,chunker.py,embedder.py,store.py}
touch RAG_Chatbot/retrieval/{__init__.py,guardrail.py,query_embedder.py,searcher.py,context_builder.py,generator.py}
touch RAG_Chatbot/ui/app.py
touch RAG_Chatbot/config/settings.py
touch RAG_Chatbot/data/sources.md
touch RAG_Chatbot/{requirements.txt,README.md,.env.example}
```

### 1.2 Install Dependencies

```bash
pip install \
  sentence-transformers \
  chromadb \
  pdfplumber \
  beautifulsoup4 \
  requests \
  streamlit \
  openai \          # or any LLM client
  python-dotenv \
  tiktoken
```

Save to `requirements.txt`:
```
sentence-transformers==2.7.0
chromadb==0.5.0
pdfplumber==0.11.0
beautifulsoup4==4.12.0
requests==2.31.0
streamlit==1.35.0
openai==1.30.0
python-dotenv==1.0.0
tiktoken==0.7.0
```

### 1.3 Config — `config/settings.py`

```python
# config/settings.py

EMBEDDING_MODEL    = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DB_PATH     = "./chroma_db"
CHROMA_COLLECTION  = "mf_faq_corpus"
TOP_K              = 4
LLM_MODEL          = "gpt-3.5-turbo"   # swap to any model
LLM_TEMPERATURE    = 0.1
MAX_TOKENS         = 300

# Chunking config
PDF_CHUNK_SIZE     = 500   # tokens
PDF_CHUNK_OVERLAP  = 50
HTML_CHUNK_SIZE    = 400
HTML_CHUNK_OVERLAP = 40
CIRC_CHUNK_SIZE    = 300
CIRC_CHUNK_OVERLAP = 30
```

### 1.4 Sources List — `data/sources.md`

Populate with all 25 official URLs from the PRD, grouped by category (AMC docs, TER, Riskometer, FAQs, SEBI/AMFI).

### Phase 1 Checklist

- [ ] Folder structure created
- [ ] All packages install without errors (`pip install -r requirements.txt`)
- [ ] `config/settings.py` contains all constants
- [ ] `data/sources.md` lists all 25 URLs
- [ ] `.env.example` created with `OPENAI_API_KEY=your_key_here`

---

## Phase 2 — Data Ingestion Pipeline

**Goal:** Load all 25 official sources, chunk them, embed each chunk, and store in ChromaDB.

Reference: `architecture.md § 2.1`

### 2.1 Loader — `ingestion/loader.py`

**Responsibility:** Fetch raw text + metadata from URLs.

```python
# ingestion/loader.py
import pdfplumber, requests, io
from bs4 import BeautifulSoup
from datetime import date

def load_pdf(url: str) -> list[dict]:
    """Download a PDF and return a list of {text, page_number, source_url, last_fetched_date}."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    pages = []
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "text": text,
                    "source_url": url,
                    "document_title": pdf.metadata.get("Title", url.split("/")[-1]),
                    "page_number": i + 1,
                    "last_fetched_date": str(date.today()),
                    "doc_type": "pdf"
                })
    return pages

def load_html(url: str) -> list[dict]:
    """Fetch an HTML page and return a list of {text, source_url, last_fetched_date}."""
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Remove scripts/styles
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    title = soup.title.string if soup.title else url
    return [{
        "text": text,
        "source_url": url,
        "document_title": title,
        "page_number": None,
        "last_fetched_date": str(date.today()),
        "doc_type": "html"
    }]

def load_source(url: str) -> list[dict]:
    """Auto-detect PDF vs HTML and load accordingly."""
    if url.endswith(".pdf"):
        return load_pdf(url)
    return load_html(url)
```

**Test:** Run `load_source("https://www.sbimf.com/faq")` → should return a list with non-empty `text`.

---

### 2.2 Chunker — `ingestion/chunker.py`

**Responsibility:** Split loaded text into chunks using an adaptive strategy.

```python
# ingestion/chunker.py
import tiktoken
from config.settings import (PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP,
                              HTML_CHUNK_SIZE, HTML_CHUNK_OVERLAP,
                              CIRC_CHUNK_SIZE, CIRC_CHUNK_OVERLAP)

enc = tiktoken.get_encoding("cl100k_base")

def _token_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping token windows."""
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        start += chunk_size - overlap
    return chunks

def chunk_document(doc: dict) -> list[dict]:
    """
    Choose chunking strategy based on doc_type.
    Returns list of chunk dicts with text + inherited metadata.
    """
    doc_type = doc.get("doc_type", "html")

    # Determine chunk parameters
    if doc_type == "pdf":
        size, overlap = PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP
    elif "sebi.gov.in" in doc.get("source_url", "") or "circular" in doc.get("document_title", "").lower():
        size, overlap = CIRC_CHUNK_SIZE, CIRC_CHUNK_OVERLAP
    else:
        size, overlap = HTML_CHUNK_SIZE, HTML_CHUNK_OVERLAP

    texts = _token_split(doc["text"], size, overlap)
    chunks = []
    for i, text in enumerate(texts):
        if text.strip():
            chunks.append({
                "text": text,
                "source_url": doc["source_url"],
                "document_title": doc["document_title"],
                "page_number": doc.get("page_number"),
                "last_fetched_date": doc["last_fetched_date"],
                "chunk_index": i
            })
    return chunks
```

**Test:** Pass a loaded HTML doc through `chunk_document()` → verify chunks are non-empty and within token limits.

---

### 2.3 Embedder — `ingestion/embedder.py`

**Responsibility:** Convert chunk text to 384-d vectors.

```python
# ingestion/embedder.py
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return a list of embedding vectors for the given texts."""
    model = get_model()
    return model.encode(texts, show_progress_bar=True).tolist()
```

**Test:** `embed_texts(["expense ratio"])` → should return a list with one 384-element vector.

---

### 2.4 Vector Store — `ingestion/store.py`

**Responsibility:** Persist chunks + embeddings in ChromaDB.

```python
# ingestion/store.py
import chromadb, uuid
from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """Insert or update chunks and their embeddings into ChromaDB."""
    collection = get_collection()
    ids       = [str(uuid.uuid4()) for _ in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{
        "source_url":       c["source_url"],
        "document_title":   c["document_title"],
        "page_number":      str(c["page_number"] or ""),
        "last_fetched_date": c["last_fetched_date"],
    } for c in chunks]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print(f"Upserted {len(chunks)} chunks into '{CHROMA_COLLECTION}'.")
```

---

### 2.5 Ingestion Orchestrator — `ingestion/run_ingestion.py`

Wire all the pieces together and run ingestion for all 25 URLs.

```python
# ingestion/run_ingestion.py
from ingestion.loader   import load_source
from ingestion.chunker  import chunk_document
from ingestion.embedder import embed_texts
from ingestion.store    import upsert_chunks

SOURCES = [
    "https://www.sbimf.com/docs/default-source/lists/kim---sbi-blue-chip-fund.pdf",
    "https://www.sbimf.com/docs/default-source/lists/sid---sbi-bluechip-fund.pdf",
    "https://www.sbimf.com/offer-document-sid-kim",
    "https://www.sbimf.com/faq",
    "https://www.sbimf.com/total-expense-ratio",
    "https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified",
    "https://www.sbimf.com/investment-options",
    "https://www.sbimf.com/kyc-procedure",
    "https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf",
    "https://www.amfiindia.com/investor",
    # ... add all 25 URLs from data/sources.md
]

def run():
    all_chunks = []
    for url in SOURCES:
        print(f"Loading: {url}")
        try:
            docs = load_source(url)
            for doc in docs:
                all_chunks.extend(chunk_document(doc))
        except Exception as e:
            print(f"  ERROR loading {url}: {e}")

    print(f"\nTotal chunks: {len(all_chunks)}")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)
    upsert_chunks(all_chunks, embeddings)
    print("Ingestion complete.")

if __name__ == "__main__":
    run()
```

Run it:
```bash
python -m ingestion.run_ingestion
```

### Phase 2 Checklist

- [ ] `loader.py` — PDFs and HTML pages load without errors
- [ ] `chunker.py` — chunks are non-empty and within token limits
- [ ] `embedder.py` — returns 384-d vectors correctly
- [ ] `store.py` — ChromaDB collection created at `./chroma_db`
- [ ] `run_ingestion.py` — all 25 URLs processed; chunk count printed
- [ ] Verify: `chroma_db/` directory exists and is non-empty after running

---

## Phase 3 — Retrieval Pipeline

**Goal:** Accept a user query, guard it, embed it, retrieve Top-K chunks, build context, and generate an answer.

Reference: `architecture.md § 2.2`

### 3.1 Guardrail — `retrieval/guardrail.py`

**Responsibility:** Classify queries before retrieval is attempted.

```python
# retrieval/guardrail.py
import re

PII_PATTERNS = [
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",          # PAN
    r"\b[2-9]{1}[0-9]{11}\b",               # Aadhaar (12-digit)
    r"\b\d{10}\b",                           # Phone number
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\w+",  # Email
    r"\botp\b", r"\bpassword\b"
]
ADVICE_KEYWORDS = [
    "should i", "should i invest", "recommend", "which fund is better",
    "best fund", "buy or sell", "should i buy", "portfolio advice",
    "which scheme should", "better option"
]
PERFORMANCE_KEYWORDS = [
    "returns", "performance", "cagr", "profit", "which gave more",
    "compare returns", "return comparison", "compare performance"
]

EDUCATIONAL_LINK = "https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified"
FACTSHEET_LINK   = "https://www.sbimf.com/factsheets"

class GuardrailResult:
    def __init__(self, allowed: bool, message: str = ""):
        self.allowed = allowed
        self.message = message

def check_query(query: str) -> GuardrailResult:
    q = query.lower()

    # PII check
    for pattern in PII_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return GuardrailResult(False,
                "For privacy reasons, please do not share personal details like PAN, "
                "Aadhaar, phone numbers, or email addresses.")

    # Advice check
    if any(k in q for k in ADVICE_KEYWORDS):
        return GuardrailResult(False,
            f"I can only answer factual questions. For investment guidance, "
            f"please consult a SEBI-registered advisor. Learn more: {EDUCATIONAL_LINK}")

    # Performance comparison check
    if any(k in q for k in PERFORMANCE_KEYWORDS):
        return GuardrailResult(False,
            f"I don't compute or compare returns. Please refer to the official "
            f"factsheets for performance data: {FACTSHEET_LINK}")

    return GuardrailResult(True)
```

---

### 3.2 Query Embedder — `retrieval/query_embedder.py`

```python
# retrieval/query_embedder.py
from ingestion.embedder import get_model

def embed_query(query: str) -> list[float]:
    """Embed a single user query using the same model as ingestion."""
    model = get_model()
    return model.encode([query])[0].tolist()
```

---

### 3.3 Searcher — `retrieval/searcher.py`

```python
# retrieval/searcher.py
from ingestion.store import get_collection
from config.settings import TOP_K

def search(query_embedding: list[float]) -> list[dict]:
    """Return Top-K chunks most similar to the query embedding."""
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "source_url": meta.get("source_url", ""),
            "document_title": meta.get("document_title", ""),
            "last_fetched_date": meta.get("last_fetched_date", ""),
            "score": round(1 - dist, 4)   # cosine similarity
        })
    return chunks
```

---

### 3.4 Context Builder — `retrieval/context_builder.py`

```python
# retrieval/context_builder.py

SYSTEM_PROMPT = """You are a facts-only Mutual Fund FAQ assistant for SBI Mutual Fund.
Rules:
- Answer ONLY from the provided context below.
- Keep answers to 3 sentences or fewer.
- Always cite exactly one source URL from the context.
- Never give investment advice or compare fund performance.
- If the context does not contain the answer, say: "I don't have enough information from official sources to answer this."
"""

def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    """
    Build the system prompt and user message for the LLM.
    Returns (system_prompt, user_message).
    """
    context_lines = []
    for i, chunk in enumerate(chunks):
        context_lines.append(
            f"[Source {i+1}: {chunk['source_url']}]\n{chunk['text']}\n"
        )
    context_block = "\n".join(context_lines)

    user_message = f"""Context:
{context_block}

Question: {query}

Answer (max 3 sentences, cite one source URL):"""

    return SYSTEM_PROMPT, user_message
```

---

### 3.5 Generator — `retrieval/generator.py`

```python
# retrieval/generator.py
import os
from openai import OpenAI
from config.settings import LLM_MODEL, LLM_TEMPERATURE, MAX_TOKENS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(system_prompt: str, user_message: str, top_chunk: dict) -> dict:
    """Call the LLM and return a structured response."""
    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ]
    )
    answer_text = response.choices[0].message.content.strip()
    return {
        "answer": answer_text,
        "source_url": top_chunk["source_url"],
        "last_fetched_date": top_chunk["last_fetched_date"]
    }
```

---

### 3.6 Retrieval Orchestrator — `retrieval/pipeline.py`

Wire all retrieval steps into a single callable function.

```python
# retrieval/pipeline.py
from retrieval.guardrail       import check_query
from retrieval.query_embedder  import embed_query
from retrieval.searcher        import search
from retrieval.context_builder import build_prompt
from retrieval.generator       import generate_answer

def answer(query: str) -> dict:
    """
    Full retrieval pipeline.
    Returns dict with keys: allowed, answer, source_url, last_fetched_date, message.
    """
    # Step 1: Guardrail
    guard = check_query(query)
    if not guard.allowed:
        return {"allowed": False, "message": guard.message}

    # Step 2: Embed query
    query_embedding = embed_query(query)

    # Step 3: Similarity search
    chunks = search(query_embedding)
    if not chunks:
        return {"allowed": True, "answer": "No relevant information found in official sources.",
                "source_url": "", "last_fetched_date": ""}

    # Step 4: Build context + prompt
    system_prompt, user_message = build_prompt(query, chunks)

    # Step 5: Generate answer
    result = generate_answer(system_prompt, user_message, chunks[0])
    result["allowed"] = True
    return result
```

**Test (CLI):**
```python
from retrieval.pipeline import answer
print(answer("What is the expense ratio of SBI Blue Chip Fund?"))
print(answer("Should I invest in this fund?"))   # Should be refused
```

### Phase 3 Checklist

- [ ] `guardrail.py` — blocks PII, advice, and performance queries correctly
- [ ] `query_embedder.py` — returns 384-d vector for any input text
- [ ] `searcher.py` — returns Top-K chunks from ChromaDB
- [ ] `context_builder.py` — produces a clean prompt with context
- [ ] `generator.py` — LLM returns a <=3-sentence answer
- [ ] `pipeline.py` — `answer()` function works end-to-end
- [ ] Test: factual query returns answer + source URL
- [ ] Test: advisory query returns refusal message (no LLM call)

---

## Phase 4 — UI Layer (Streamlit)

**Goal:** Build a minimal, clean chat UI with example questions, disclaimer, and properly formatted responses.

Reference: `architecture.md § 2.3`, `PRD.md § 6.4`

### 4.1 `ui/app.py`

```python
# ui/app.py
import streamlit as st
from retrieval.pipeline import answer

# --- Page Config ---
st.set_page_config(
    page_title="SBI MF FAQ Assistant",
    page_icon="📊",
    layout="centered"
)

# --- Header ---
st.title("📊 SBI Mutual Fund FAQ Assistant")
st.caption("Facts-only. No investment advice.")
st.markdown("---")

# --- Example Questions ---
st.markdown("**Try asking:**")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💡 Expense ratio of SBI Blue Chip Fund?"):
        st.session_state["prefill"] = "What is the expense ratio of SBI Blue Chip Fund?"
with col2:
    if st.button("💡 ELSS lock-in period?"):
        st.session_state["prefill"] = "What is the ELSS lock-in period?"
with col3:
    if st.button("💡 How to download capital-gains statement?"):
        st.session_state["prefill"] = "How do I download my capital-gains statement?"

# --- Chat History ---
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Input ---
prefill = st.session_state.pop("prefill", "")
query = st.chat_input("Ask a factual question about SBI MF schemes...")
if prefill:
    query = prefill

if query:
    st.session_state["history"].append({"role": "user", "content": query})
    with st.spinner("Looking up official sources..."):
        result = answer(query)

    if not result["allowed"]:
        response_text = result["message"]
        st.session_state["history"].append({"role": "assistant", "content": response_text})
    else:
        response_text = (
            f"{result['answer']}\n\n"
            f"📎 **Source:** {result['source_url']}\n\n"
            f"🗓️ **Last updated from sources:** {result['last_fetched_date']}"
        )
        st.session_state["history"].append({"role": "assistant", "content": response_text})

# --- Render Chat ---
for msg in st.session_state["history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Disclaimer Footer ---
st.markdown("---")
st.caption(
    "⚠️ **Disclaimer:** This assistant provides factual information only from official "
    "SBI MF, SEBI, and AMFI sources. It does not provide investment advice, "
    "recommend schemes, or compute performance. For investment decisions, "
    "consult a SEBI-registered investment advisor."
)
```

### 4.2 Run the App

```bash
streamlit run ui/app.py
```

### Phase 4 Checklist

- [ ] App launches at `http://localhost:8501`
- [ ] Welcome title, caption, and 3 example buttons visible
- [ ] Example question buttons pre-fill and submit a query
- [ ] Factual query returns: answer + source URL + last-updated date
- [ ] Refused query shows polite message with a redirect link
- [ ] Disclaimer footer is always visible
- [ ] Chat history persists within the session

---

## Phase 5 — Polish & Deliverables

**Goal:** QA the full system and produce all required submission artifacts.

### 5.1 End-to-End QA

Test the following queries manually and verify output:

| # | Query | Expected Outcome |
|---|---|---|
| 1 | What is the expense ratio of SBI Blue Chip Fund? | Factual answer + TER source URL |
| 2 | What is the ELSS lock-in period? | 3 years — factual answer + SID/KIM source |
| 3 | What is the minimum SIP amount? | Factual answer + source |
| 4 | How do I download my capital-gains statement? | Steps + statement portal URL |
| 5 | What is the exit load for SBI Bluechip Fund? | Factual answer + KIM/SID source |
| 6 | What is the riskometer of SBI Flexicap Fund? | Factual answer + riskometer source |
| 7 | Should I invest in SBI Bluechip Fund? | Refusal + educational link |
| 8 | Which fund gave better returns? | Refusal + factsheet link |
| 9 | My PAN is ABCDE1234F, what are my holdings? | Privacy notice, no retrieval |
| 10 | What is KYC and how do I complete it? | Factual answer + KYC URL |

### 5.2 Sample Q&A File — `sample_qa.md`

For each of the 10 queries above, record:
- The query
- The assistant's actual answer (copy from UI)
- The source URL returned

### 5.3 Source List — `data/sources.md`

Final CSV-style markdown table of the URLs actually used during ingestion (from the 25 listed in the PRD).

### 5.4 Disclaimer Snippet

Use this verbatim in the UI footer and README:

```
This assistant provides factual information only from official SBI MF, SEBI,
and AMFI public sources. It does not provide investment advice, recommend
schemes, or compute performance. For investment decisions, consult a
SEBI-registered investment advisor.
```

### 5.5 README — `README.md`

Must cover:

1. **Project scope** — SBI MF FAQ chatbot, facts-only
2. **Setup steps:**
   ```bash
   git clone <repo>
   cd RAG_Chatbot
   pip install -r requirements.txt
   cp .env.example .env   # add your OPENAI_API_KEY
   python -m ingestion.run_ingestion
   streamlit run ui/app.py
   ```
3. **AMC & Schemes covered** — SBI MF: Blue Chip, Flexicap, ELSS, Index Funds, Small Cap
4. **Known limitations:**
   - Static corpus (no live NAV)
   - SBI MF only (single AMC)
   - ChromaDB is local; not production-hosted

### Phase 5 Checklist

- [ ] All 10 QA queries tested and produce correct output
- [ ] `sample_qa.md` — 10 queries with actual answers and source URLs
- [ ] `data/sources.md` — final source list complete
- [ ] `README.md` — setup steps, scope, and limitations documented
- [ ] Disclaimer snippet in UI footer and README
- [ ] Prototype runs end-to-end: `run_ingestion` → `streamlit run ui/app.py`

---

## Summary — Phase Dependencies

```
Phase 1 (Setup)
    |
    v
Phase 2 (Ingestion: Loader → Chunker → Embedder → ChromaDB)
    |
    v
Phase 3 (Retrieval: Guardrail → Search → Context → LLM)
    |
    v
Phase 4 (UI: Streamlit app)
    |
    v
Phase 5 (Polish: QA + Deliverables)
```

> Each phase depends on the previous. Do not skip ahead — each phase produces artifacts consumed by the next.
