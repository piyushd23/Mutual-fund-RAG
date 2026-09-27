# Architecture Document
## Mutual Fund FAQ RAG Chatbot

| Field | Detail |
|---|---|
| **Project** | Mutual Fund FAQs — Facts-Only RAG Chatbot |
| **Version** | 1.0 |
| **Status** | Draft |
| **Date** | 2026-09-27 |

---

## 1. High-Level System Architecture

The system is split into two major phases: **Data Ingestion** (offline, one-time or scheduled) and **Data Retrieval** (real-time, per user query).

```
=======================================================================
                         DATA INGESTION (Offline)
=======================================================================

  [ Official URLs ]
  AMC / SEBI / AMFI
  (PDFs + HTML pages)
         |
         v
  +-------------+     +---------------+     +--------------------+     +-------------+
  |   Loader    | --> |    Chunker    | --> | Embedding Model    | --> |  ChromaDB   |
  | (PDF/HTML)  |     | (Adaptive)    |     | all-MiniLM-L6-v2   |     | Vector Store|
  +-------------+     +---------------+     +--------------------+     +-------------+
         |                   |                        |                       |
   Raw text +          Chunks with              Dense vector            Vectors +
   metadata            metadata                 embeddings              metadata
                       (source_url,                                     stored
                        doc_title,
                        page_no,
                        fetched_date)


=======================================================================
                         DATA RETRIEVAL (Real-Time)
=======================================================================

  [ User Query ]
         |
         v
  +------------------+
  |  Query Guardrail |  <-- PII check, advice check, performance check
  +------------------+
         |
    [PASS / FAIL]
         |
       PASS                              FAIL
         |                                |
         v                                v
  +------------------+         +----------------------+
  | Embed Query      |         | Refusal Handler      |
  | all-MiniLM-L6-v2|         | (polite message +    |
  +------------------+         |  educational link)   |
         |                     +----------------------+
         v
  +------------------+
  |  ChromaDB        |
  |  Similarity      |
  |  Search (Top-K)  |
  +------------------+
         |
         v
  +------------------+
  |  Context Builder |  <-- Assemble Top-K chunks + source metadata
  +------------------+
         |
         v
  +------------------+
  |  LLM             |  <-- Generate answer (<=3 sentences)
  |  (Prompt + RAG)  |
  +------------------+
         |
         v
  +------------------+
  |  Response        |  <-- Answer + Source URL + Last Updated Date
  |  Formatter       |
  +------------------+
         |
         v
  [ User Interface ]
```

---

## 2. Component Breakdown

### 2.1 Data Ingestion Layer

#### 2.1.1 Loader

**Responsibility:** Fetch raw content from official URLs and extract clean text.

| Input Type | Loader Tool | Output |
|---|---|---|
| PDF documents (SID, KIM, SAI, circulars) | `PyPDF2` / `pdfplumber` | Raw text per page |
| HTML web pages (FAQs, TER, investment options) | `BeautifulSoup` / `requests` | Raw text per section |

**Key metadata extracted at load time:**
- `source_url` — the original official URL
- `document_title` — PDF title or HTML `<title>` tag
- `page_number` — PDF page number (N/A for HTML)
- `last_fetched_date` — ISO timestamp of fetch

---

#### 2.1.2 Chunker

**Responsibility:** Split raw text into semantically meaningful chunks suitable for embedding.

| Document Type | Strategy | Chunk Size | Overlap |
|---|---|---|---|
| PDFs (SID / KIM / SAI) | Section-based — split on headings / section titles | ~500 tokens | 50 tokens |
| HTML / Web pages (FAQs, TER) | Semantic — split on Q&A pairs or `<h2>`/`<p>` boundaries | ~400 tokens | 40 tokens |
| Short regulatory circulars | Fixed-size | 300 tokens | 30 tokens |

**Chunk object schema:**
```json
{
  "chunk_id": "uuid",
  "text": "...chunk content...",
  "source_url": "https://...",
  "document_title": "SBI Blue Chip Fund KIM",
  "page_number": 3,
  "last_fetched_date": "2026-09-27"
}
```

---

#### 2.1.3 Embedding Model

| Property | Value |
|---|---|
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Type** | Bi-encoder (dense retrieval) |
| **Output** | 384-dimensional float vector per chunk |
| **Why this model** | Lightweight, fast, good semantic similarity for short factual text |

Each chunk's text is passed through the model to produce a fixed-size embedding vector, which is then stored alongside the chunk metadata in ChromaDB.

---

#### 2.1.4 Vector Store — ChromaDB

**Responsibility:** Persist embeddings and chunk metadata; serve similarity queries.

| Property | Value |
|---|---|
| **DB** | ChromaDB (local persistent) |
| **Collection name** | `mf_faq_corpus` |
| **Distance metric** | Cosine similarity |
| **Top-K retrieval** | K = 3–5 (tunable) |

**Stored fields per record:**
- `embedding` — 384-d float vector
- `document` — chunk text
- `metadata` — `{source_url, document_title, page_number, last_fetched_date}`

---

### 2.2 Data Retrieval Layer

#### 2.2.1 Query Guardrail

**Responsibility:** Classify the user query before any retrieval is attempted. Acts as the first filter.

```
User Query
    |
    v
+-------------------------------+
|  Is PII present?              |  --> YES --> Privacy Notice (no retrieval)
|  (PAN / Aadhaar / OTP /       |
|   phone / email patterns)     |
+-------------------------------+
    |
    v
+-------------------------------+
|  Is it advisory?              |  --> YES --> Refusal + Educational Link
|  ("Should I invest?",         |
|   "Best fund for me?")        |
+-------------------------------+
    |
    v
+-------------------------------+
|  Is it a performance query?   |  --> YES --> Redirect to Official Factsheet
|  ("Returns of X vs Y?")       |
+-------------------------------+
    |
    v
  [FACTUAL QUERY — proceed to retrieval]
```

---

#### 2.2.2 Query Embedder

- Uses the **same model** as the ingestion step (`all-MiniLM-L6-v2`) to embed the user query.
- Ensures the query and corpus live in the same vector space.

---

#### 2.2.3 Similarity Search

- Query vector is sent to **ChromaDB**.
- Returns **Top-K chunks** (K=3–5) ranked by cosine similarity.
- Each result includes the chunk text and its metadata (`source_url`, `document_title`, `last_fetched_date`).

---

#### 2.2.4 Context Builder

**Responsibility:** Assemble the retrieved chunks into a structured prompt context.

```
SYSTEM PROMPT:
  "You are a facts-only Mutual Fund FAQ assistant.
   Answer only from the provided context.
   Do not give investment advice.
   Keep answers to <=3 sentences.
   Always cite exactly one source URL."

CONTEXT:
  [Chunk 1 text]  (Source: <url_1>)
  [Chunk 2 text]  (Source: <url_2>)
  ...

USER QUESTION:
  "<user query>"
```

---

#### 2.2.5 LLM

**Responsibility:** Generate a concise, factual answer from the assembled prompt.

| Property | Value |
|---|---|
| **Model** | TBD — GPT-3.5 / open-source (e.g., Mistral-7B) |
| **Max answer length** | <=3 sentences |
| **Temperature** | Low (0.0–0.2) for factual consistency |
| **Instruction** | Facts-only; cite one source; no advice |

---

#### 2.2.6 Response Formatter

**Responsibility:** Structure the LLM output into the final user-facing response.

```
[Answer text — <=3 sentences]

Source: https://...
Last updated from sources: 2026-09-27
```

---

### 2.3 UI Layer

**Responsibility:** Simple, clean interface for the user to interact with the chatbot.

| Element | Description |
|---|---|
| **Welcome line** | "Welcome! Ask me facts about SBI Mutual Fund schemes." |
| **Example questions** | 3 clickable example prompts shown on load |
| **Chat input** | Single text input field |
| **Response area** | Shows answer + source + last-updated date |
| **Disclaimer** | Fixed footer: *"Facts-only. No investment advice."* |

---

## 3. Data Flow Summary

```
[Source URLs] --> Loader --> Chunker --> Embedding Model --> ChromaDB
                                                                |
[User Query] --> Guardrail --> Query Embedder --> Similarity Search (ChromaDB)
                                                                |
                                                         Top-K Chunks
                                                                |
                                                       Context Builder
                                                                |
                                                              LLM
                                                                |
                                                     Response Formatter
                                                                |
                                                          [User UI]
```

---

## 4. Module / File Structure

```
RAG_Chatbot/
├── ingestion/
│   ├── loader.py           # PDF + HTML fetching and text extraction
│   ├── chunker.py          # Adaptive chunking logic (PDF / HTML / circular)
│   ├── embedder.py         # Embedding generation using all-MiniLM-L6-v2
│   └── store.py            # ChromaDB write operations (upsert chunks)
│
├── retrieval/
│   ├── guardrail.py        # Query classification (PII / advice / performance)
│   ├── query_embedder.py   # Embed user query (same model as ingestion)
│   ├── searcher.py         # ChromaDB similarity search (Top-K)
│   ├── context_builder.py  # Assemble prompt from retrieved chunks
│   └── generator.py        # LLM call + response formatting
│
├── ui/
│   └── app.py              # Streamlit / Gradio / FastAPI UI
│
├── data/
│   └── sources.md          # Master list of 25 official source URLs
│
├── config/
│   └── settings.py         # Model names, K value, chunk sizes, DB path
│
├── PRD.md
├── architecture.md
├── README.md
└── requirements.txt
```

---

## 5. Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Embedding model | `all-MiniLM-L6-v2` | Lightweight, fast, strong semantic similarity, no GPU required |
| Vector DB | ChromaDB | Fully local, no external service, easy to set up, Python-native |
| Chunking | Adaptive (doc-type aware) | PDFs and HTML have very different structures; one-size chunking loses context |
| LLM temperature | 0.0–0.2 | Factual tasks need deterministic, consistent answers |
| Top-K | 3–5 | Enough context without overwhelming the LLM prompt |
| Storage of PII | None | Hard constraint from PRD — no PII at any layer |

---

## 6. Constraints & Guard Rails

| Layer | Guardrail |
|---|---|
| **Loader** | Only fetch from the 25 approved official URLs |
| **Query Classifier** | Reject PII, advice queries, performance comparison before retrieval |
| **LLM Prompt** | System instruction explicitly forbids advice and return calculation |
| **Response Formatter** | Always appends one source URL and a last-updated date |
| **UI** | Permanent disclaimer footer; no form fields that could collect PII |

---

## 7. Sequence Diagram — Happy Path (Factual Query)

```
User          UI         Guardrail    QueryEmbedder    ChromaDB    ContextBuilder    LLM      Formatter
 |             |               |              |              |              |           |           |
 |-- query --> |               |              |              |              |           |           |
 |             |-- classify -> |              |              |              |           |           |
 |             |   [PASS]      |              |              |              |           |           |
 |             |-- embed ------------------>  |              |              |           |           |
 |             |               |         [384-d vector]      |              |           |           |
 |             |-- search ---------------------------------> |              |           |           |
 |             |               |              |         [Top-K chunks]      |           |           |
 |             |-- build context ----------------------------------------> |           |           |
 |             |               |              |              |        [prompt]          |           |
 |             |-- generate ---------------------------------------------------------> |           |
 |             |               |              |              |              |     [raw answer]      |
 |             |-- format --------------------------------------------------------------------->   |
 |             |               |              |              |              |           |  [formatted]
 | <-- response|               |              |              |              |           |           |
```

---

## 8. Sequence Diagram — Refusal Path (Advisory Query)

```
User          UI         Guardrail
 |             |               |
 |-- "Should I invest?" ->     |
 |             |-- classify -> |
 |             |   [FAIL — advisory]
 |             |<-- refusal message + educational link
 | <-- response|
```

---

## 9. Known Limitations & Future Improvements

| Limitation | Mitigation / Future Work |
|---|---|
| Static corpus (no live NAV data) | Schedule periodic re-ingestion (weekly/monthly) |
| Single AMC (SBI MF only in v1) | Add more AMC corpora in v2 |
| LLM hallucination risk | Low temperature + strict system prompt + source grounding |
| ChromaDB is local-only | Migrate to hosted vector DB (e.g., Pinecone, Weaviate) for production |
| No user session memory | Stateless is intentional for privacy; add optional session context in v2 |
