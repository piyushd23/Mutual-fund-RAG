# SBI Mutual Fund FAQ RAG Assistant

A production-grade, factual Retrieval-Augmented Generation (RAG) assistant for SBI Mutual Fund schemes, investor services, tax rules, and NAV queries.

Built with **FastAPI**, **ChromaDB**, **Sentence-Transformers (`all-MiniLM-L6-v2`)**, and a sleek **HTML5/CSS3/JS Web UI** designed for seamless deployment.

---

## 🚀 Key Features

- **No Streamlit Dependency**: Replaced with a fast, lightweight FastAPI backend and responsive single-page web app.
- **Easy One-Command Deployment**: Ready for Docker, Render, Railway, Hugging Face Spaces, Fly.io, or AWS.
- **RESTful API Included**: Exposes `/api/chat`, `/api/stats`, `/api/health`, and interactive Swagger docs at `/docs`.
- **Zero API Key Requirement (Local Mode)**: Default `local` mode retrieves verified factual quotes directly from the indexed corpus. Also supports Groq (Llama-3) and OpenAI.
- **Strict Financial Guardrails**: Automatically detects and refuses requests for personal financial advice, speculative returns, or sensitive PII (PAN, Aadhaar).
- **Verifiable Citations**: Every answer links directly to the official SBI MF / SEBI / AMFI source document with last-fetched dates and expandable context snippets.
- **690+ Chunks Indexed**: Persistent local ChromaDB collection covering official SBI MF Scheme Information Documents (SIDs), Key Information Memorandums (KIMs), FAQs, and Total Expense Ratio disclosures.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Web Server** | FastAPI + Uvicorn | High-performance async REST API & static file serving |
| **Frontend UI** | HTML5, Modern Vanilla CSS, Vanilla JS | Lightweight, zero-build client with dark glassmorphism |
| **Vector DB** | ChromaDB (`chroma_db/`) | Persistent vector database storing 690 chunks |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional dense semantic vector representations |
| **Guardrails** | Regex & Rule-Based Intent Filter | Rejects financial advice and PII before search/generation |

---

## ⚡ Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
The project works out of the box with zero configuration (`GENERATOR_MODE=local`):
```bash
cp .env.example .env
```
Supported `GENERATOR_MODE` values:
- `local` *(default)*: Offline, returns top retrieved chunk directly (no API key needed).
- `groq`: Free cloud Llama-3 via [Groq Console](https://console.groq.com) (`GROQ_API_KEY=...`).
- `openai`: Cloud GPT-3.5/4 (`OPENAI_API_KEY=...`).

### 3. Start the Web Application
```bash
python3 run.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🚢 Cloud & Production Deployment

### Option A: Docker
```bash
# Build container image
docker build -t sbi-mf-rag .

# Run container on port 8000
docker run -d -p 8000:8000 --name sbi-mf-assistant sbi-mf-rag
```

### Option B: Render / Railway / Heroku
The repository includes a ready-to-use [`Procfile`](file:///Users/piyushdeshmukh/RAG_Chatbot/Procfile):
```text
web: uvicorn ui.server:app --host 0.0.0.0 --port $PORT
```
1. Connect your Git repository to Render or Railway.
2. Select **Python** environment.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python3 run.py` (or let the platform read `Procfile`).

---

## 📡 REST API Reference

The server automatically provides interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### `POST /api/chat`
Process a natural-language inquiry through the RAG pipeline.

**Request:**
```json
{
  "query": "What is the expense ratio of SBI Blue Chip Fund?"
}
```

**Response (Factual Answer):**
```json
{
  "allowed": true,
  "answer": "Actual expenses for the previous financial year ending March 31, 2024: Scheme Name Regular Plan Direct Plan SBI Blue Chip Fund 1.54% 0.85%...",
  "source_url": "https://www.sbimf.com/docs/default-source/lists/kim---sbi-blue-chip-fund.pdf",
  "last_fetched_date": "2026-09-27",
  "mode": "local",
  "sources": [
    {
      "doc_title": "SBI MF Document",
      "source_url": "https://www.sbimf.com/...",
      "last_fetched_date": "2026-09-27",
      "preview": "..."
    }
  ]
}
```

**Response (Guardrail Refusal):**
```json
{
  "allowed": false,
  "message": "I can only answer factual questions about mutual fund schemes. For personalised investment guidance, please consult a SEBI-registered investment advisor.",
  "reason": "advice"
}
```

### `GET /api/stats`
Returns system status, active embedding model, generator mode, and ChromaDB indexed chunk count.

### `GET /api/health`
Lightweight healthcheck endpoint for load balancers and container orchestrators.

---

## 📚 Source List (Knowledge Base)

The persistent ChromaDB vector database is populated from the following official sources:
1. **Scheme Information Documents (SIDs):** Including SBI Blue Chip Fund, SBI ELSS Tax Saver Fund.
2. **Key Information Memorandums (KIMs):** Extracted financial limits, expense ratios, and lock-in periods.
3. **SBI Mutual Fund Website:** Official FAQ portals, Grievance Redressal, KYC Procedures, Investment Options, and Capital Gains Statement guides.
4. **Regulatory Bodies:** AMFI Investor Education portal and SEBI compliance guidelines.

---

## 💬 Sample Q&A

**User:** What is the lock-in period for ELSS mutual funds?
**Assistant:** ELSS mutual funds, including the SBI ELSS Tax Saver Fund, have a mandatory statutory lock‑in period of three years from the date of allotment. During this period, units cannot be redeemed, switched, or withdrawn. *(Source: https://www.sbimf.com/?fund=elss-tax-saver)*

**User:** Can you suggest the best mutual fund for me to invest 1 lakh rupees?
**Assistant:** I can only answer factual questions about mutual fund schemes. For personalised investment guidance, please consult a SEBI-registered investment advisor. *(Blocked by Guardrail)*

**User:** How do I download my Capital Gains Statement?
**Assistant:** You can download your Capital Gains statement by logging into your dashboard on the official sbimf.com portal and navigating to the 'Statements' section. Alternatively, you can use MFCentral or request it via email from CAMS / KFintech. *(Source: https://www.sbimf.com/?page=capital-gains)*

---

## ⚠️ Regulatory Compliance & Disclaimer
**Mutual Fund investments are subject to market risks. Read all scheme related documents carefully.** 

This application is an experimental Retrieval-Augmented Generation (RAG) assistant. It provides factual answers extracted dynamically from official SBI Mutual Fund, SEBI, and AMFI publications. **It does not offer financial, tax, or investment advice.** The developer assumes no liability for investment decisions made based on this tool. Always consult a SEBI-registered investment advisor for personal financial planning.
