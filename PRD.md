# Product Requirements Document (PRD)
## Mutual Fund FAQ RAG Chatbot

| Field | Detail |
|---|---|
| **Project Name** | Mutual Fund FAQs — Facts-Only RAG Chatbot |
| **Version** | 1.0 |
| **Status** | Draft |
| **Date** | 2026-09-27 |

---

## 1. Overview

Build a **Retrieval-Augmented Generation (RAG) chatbot** that answers factual questions about SBI Mutual Fund schemes using only official public sources (AMC / SEBI / AMFI). Every answer must cite exactly one source link. The assistant must never give investment advice.

---

## 2. Problem Statement

Retail investors and support/content teams repeatedly look up the same factual details about mutual fund schemes — expense ratios, exit loads, SIP minimums, ELSS lock-in periods, riskometers, benchmarks, and how to download statements. There is no single, fast, citation-backed assistant that answers these questions without crossing into investment advice.

---

## 3. Target Users

| User Type | Need |
|---|---|
| Retail investors | Quick factual lookups while comparing schemes |
| Support/content teams | Accurate, repeatable answers to common MF questions |

---

## 4. Goals & Non-Goals

### Goals
- Answer **factual** queries about SBI MF schemes using official public pages.
- Provide **one citation link** per answer.
- Refuse advisory/opinionated questions politely and redirect to educational resources.
- Maintain a **tiny, clean UI** with example questions and a disclaimer.
- Follow the complete **RAG pipeline**: Loading → Chunking → Embedding → Vector Store → Retrieval → Generation.

### Non-Goals
- Investment advice or portfolio recommendations.
- Performance comparison or return calculations.
- Collecting or storing any PII (PAN, Aadhaar, OTP, email, phone).
- Using third-party blogs or unofficial sources.

---

## 5. RAG Architecture

```
+-----------------------------------------------------+
|                  DATA INGESTION                     |
|                                                     |
|  Public URLs (PDFs + Web pages)                     |
|         |                                           |
|         v                                           |
|     Loading --> Chunking --> Embedding --> ChromaDB  |
+-----------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------+
|                  DATA RETRIEVAL                     |
|                                                     |
|  User Query --> Embed Query --> Similarity Search   |
|                                      |              |
|                                      v              |
|                              Top-K Chunks           |
|                                      |              |
|                                      v              |
|                           LLM (with context)        |
|                                      |              |
|                                      v              |
|                    Answer (<=3 sentences) + Citation |
+-----------------------------------------------------+
```

### 5.1 Technical Stack

| Component | Choice |
|---|---|
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector DB** | ChromaDB |
| **Chunking Strategy** | Adaptive — based on document type (PDF vs. HTML); see Section 6.2 |
| **LLM** | TBD (e.g., GPT-3.5 / open-source equivalent) |

---

## 6. Functional Requirements

### 6.1 Data Ingestion Pipeline

#### Corpus Sources (25 official URLs)

**AMC Scheme Documents (SID / KIM / Factsheet)**

| # | URL | Description |
|---|---|---|
| 1 | https://www.sbimf.com/docs/default-source/lists/kim---sbi-blue-chip-fund.pdf | KIM, SBI Blue Chip Fund |
| 2 | https://www.sbimf.com/docs/default-source/lists/sid---sbi-bluechip-fund.pdf | SID, SBI Bluechip Fund |
| 3 | https://www.sbimf.com/offer-document-sid-kim | SID/KIM hub (all schemes, differentiation tables) |
| 4 | https://www.sbimf.com/sid-kim-archive | SID/KIM archive |
| 5 | https://www.sbimf.com/factsheets | Monthly factsheets hub (all schemes) |
| 6 | https://www.sbimf.com/portfolios | Scheme portfolio disclosures |
| 7 | https://www.sbimf.com/docs/default-source/documents/statement-of-additional-information.pdf | SAI |
| 8 | https://www.sbimf.com/docs/default-source/pdf/equity-schemes---scheme-differentiation.pdf | Equity scheme differentiation table |

**Fees / Charges / TER**

| # | URL | Description |
|---|---|---|
| 9 | https://www.sbimf.com/total-expense-ratio | TER of all schemes |
| 10 | https://www.sbimf.com/forms | Forms & downloads hub |

**Riskometer / Benchmark**

| # | URL | Description |
|---|---|---|
| 11 | https://www.sbimf.com/docs/default-source/pdf/index-funds---scheme-differentiation.pdf | Benchmark differentiation reference |
| 12 | https://www.sebi.gov.in/legal/circulars/oct-2020/circular-on-product-labeling-in-mutual-fund-schemes-risk-o-meter_47796.html | SEBI Riskometer circular 2020 (landing page) |
| 13 | https://www.sebi.gov.in/sebi_data/attachdocs/oct-2020/1602580413614.pdf | Full SEBI Riskometer circular PDF |
| 14 | https://www.sebi.gov.in/sebi_data/attachdocs/1430388883147.pdf | SEBI Product Labeling circular 2015 |
| 15 | https://compfie.aparajitha.com/wp-content/uploads/2021/09/02092021_FCC_03.pdf | SEBI riskometer/benchmark/portfolio circular 2021 |

**Scheme FAQs / Investor Education**

| # | URL | Description |
|---|---|---|
| 16 | https://www.sbimf.com/faq | SBI MF FAQs |
| 17 | https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified | Jargon/terms glossary |
| 18 | https://www.sbimf.com/investment-options | Growth/IDCW, SIP/STP/SWP explainer |

**Statement / Tax-Document Guides**

| # | URL | Description |
|---|---|---|
| 19 | https://www.sbimf.com/kyc-procedure | KYC procedure |
| 20 | https://online.sbimf.com/statement | Statement of Account portal |
| 21 | https://www.sbimf.com/idcw-history | IDCW (dividend) history |
| 22 | https://www.sbimf.com/grievance-redressal | Grievance redressal procedure |

**SEBI / AMFI Regulatory Layer**

| # | URL | Description |
|---|---|---|
| 23 | https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf | SEBI Investor Charter (rights, timelines, grievance) |
| 24 | https://www.amfiindia.com/ | AMFI homepage |
| 25 | https://www.amfiindia.com/investor | AMFI investor resources |

---

### 6.2 Chunking Strategy

The chunking strategy is adaptive based on document type:

| Document Type | Recommended Strategy |
|---|---|
| **PDFs (SID / KIM / SAI)** | Section-based chunking — split on headings/section titles; ~500 tokens, 50-token overlap |
| **HTML / Web pages (FAQs, TER)** | Semantic chunking — split on Q&A pairs or `<h2>`/`<p>` boundaries |
| **Short regulatory circulars** | Fixed-size chunking — 300 tokens, 30-token overlap |

**Metadata to store per chunk:**
- `source_url`
- `document_title`
- `page_number` (PDFs only)
- `last_fetched_date`

---

### 6.3 Query Handling

| Query Type | Behavior |
|---|---|
| Factual (expense ratio, exit load, min SIP, ELSS lock-in, riskometer, how-to guides) | Answer in <=3 sentences + one citation link |
| Opinionated / advisory ("Should I invest?", "Best fund?") | Politely refuse + redirect to an educational link |
| PII input (PAN, Aadhaar, OTP, phone, email) | Do not accept or store; respond with a privacy notice |
| Return / performance comparison | Do not compute; link to official factsheet |

---

### 6.4 UI Requirements

- **Welcome line** at the top introducing the assistant.
- **3 example questions** displayed on load:
  - *"What is the expense ratio of SBI Blue Chip Fund?"*
  - *"What is the ELSS lock-in period?"*
  - *"How do I download my capital-gains statement?"*
- **Disclaimer note**: `"Facts-only. No investment advice."`
- **Each answer** must show:
  - Answer text (<=3 sentences)
  - `Source: <url>`
  - `Last updated from sources: <date>`

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Privacy** | No PII collected, stored, or logged at any stage |
| **Source integrity** | Only official AMC/SEBI/AMFI URLs; no third-party blogs |
| **Answer length** | <=3 sentences per answer |
| **Citation** | Every answer must include exactly one source link |
| **Transparency** | Display "Last updated from sources: `<date>`" in every response |
| **Performance claims** | Strictly prohibited; link to official factsheet instead |

---

## 8. Constraints

| Type | Constraint |
|---|---|
| Sources | Public sources only — no third-party blogs or unofficial data |
| Privacy | No PII: no PAN, Aadhaar, OTP, email, or phone numbers |
| Advice | No investment advice of any kind |
| Performance | No return computation or fund performance comparison |
| Citation | Every answer must cite its source |

---

## 9. Deliverables

| # | Deliverable | Description |
|---|---|---|
| 1 | **Working Prototype** | Runnable app/notebook or <=3-min demo video |
| 2 | **Source List** | CSV or MD listing the URLs used |
| 3 | **README** | Setup steps, AMC/scheme scope, known limitations |
| 4 | **Sample Q&A File** | 5–10 queries with assistant answers and citation links |
| 5 | **Disclaimer Snippet** | Facts-only, no-advice disclaimer text used in the UI |

---

## 10. Out of Scope (v1)

- Multi-AMC support (only SBI MF in v1)
- Real-time NAV or live price feeds
- User authentication or account management
- Mobile application
- Portfolio tracking or personalization

---

## 11. Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — retrieve relevant chunks from a vector store, then generate an answer using an LLM |
| **SID** | Scheme Information Document |
| **KIM** | Key Information Memorandum |
| **SAI** | Statement of Additional Information |
| **TER** | Total Expense Ratio |
| **ELSS** | Equity Linked Savings Scheme |
| **IDCW** | Income Distribution cum Capital Withdrawal (formerly dividend) |
| **SIP / STP / SWP** | Systematic Investment / Transfer / Withdrawal Plan |
| **ChromaDB** | Open-source vector database for storing embeddings |
| **all-MiniLM-L6-v2** | Lightweight sentence-transformer model for generating text embeddings |
