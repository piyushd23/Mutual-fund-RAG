# ui/app.py
# Phase 4: Streamlit chat UI for the SBI MF FAQ RAG Chatbot.
# Features:
#   - Custom CSS for a premium look
#   - Sidebar with corpus info + ingestion status
#   - 3 clickable example question chips
#   - Chat history with styled message bubbles
#   - Factual answers show source card + last-updated date
#   - Refused queries show clear, styled notice
#   - Permanent disclaimer footer

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()  # must run before any os.getenv calls

import streamlit as st
from retrieval.pipeline import answer
from ingestion.store import collection_count

# ============================================================
# PAGE CONFIG — must be first Streamlit call
# ============================================================
st.set_page_config(
    page_title="SBI MF FAQ Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
/* ---- Global ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---- Header ---- */
.main-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #1a73e8, #0d47a1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.main-subtitle {
    color: #5f6368;
    font-size: 0.95rem;
    margin-top: 4px;
    margin-bottom: 20px;
}

/* ---- Example chip buttons ---- */
div.stButton > button {
    border-radius: 20px !important;
    border: 1.5px solid #1a73e8 !important;
    color: #1a73e8 !important;
    background: #f8f9ff !important;
    font-size: 0.82rem !important;
    padding: 4px 12px !important;
    transition: all 0.2s ease;
    white-space: normal !important;
    height: auto !important;
}
div.stButton > button:hover {
    background: #1a73e8 !important;
    color: white !important;
}

/* ---- Source card ---- */
.source-card {
    background: #f0f7ff;
    border-left: 4px solid #1a73e8;
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 10px;
    font-size: 0.85rem;
}
.source-card a {
    color: #1a73e8;
    text-decoration: none;
    word-break: break-all;
}
.source-card a:hover {
    text-decoration: underline;
}

/* ---- Refusal notice ---- */
.refusal-box {
    background: #fff8e1;
    border-left: 4px solid #f9a825;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.9rem;
    color: #5f4f00;
    margin-top: 6px;
}

/* ---- Disclaimer ---- */
.disclaimer {
    background: #f1f3f4;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.78rem;
    color: #5f6368;
    margin-top: 20px;
    line-height: 1.5;
}

/* ---- Sidebar corpus badge ---- */
.corpus-badge {
    background: #e8f5e9;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.82rem;
    color: #1b5e20;
    margin-bottom: 10px;
}
.corpus-badge-warn {
    background: #fff3e0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.82rem;
    color: #e65100;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 📊 SBI MF FAQ Assistant")
    st.markdown("---")

    # Corpus / DB status
    st.markdown("### ⚙️ Generator Mode")
    mode = os.getenv("GENERATOR_MODE", "local")
    mode_labels = {
        "local":  "🟢 Local (no API key)",
        "groq":   "🔵 Groq — Llama3 (free)",
        "openai": "🟠 OpenAI GPT",
    }
    st.markdown(
        f'<div class="corpus-badge">{mode_labels.get(mode, mode)}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 🗄️ Knowledge Base")
    try:
        count = collection_count()
        if count > 0:
            st.markdown(
                f'<div class="corpus-badge">✅ <b>{count}</b> chunks loaded<br>'
                f'ChromaDB · persistent</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="corpus-badge-warn">⚠️ ChromaDB is empty.<br>'
                'Run ingestion first:<br>'
                '<code>python3 -m ingestion.run_ingestion</code></div>',
                unsafe_allow_html=True,
            )
    except Exception:
        st.markdown(
            '<div class="corpus-badge-warn">⚠️ ChromaDB not initialised.<br>'
            'Run ingestion first.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("### 📚 Corpus Scope")
    st.markdown("""
- **AMC:** SBI Mutual Fund
- **Schemes:** Blue Chip, Flexicap, ELSS, Small Cap, Index Funds
- **Sources:** 25 official AMC / SEBI / AMFI pages
- **Embedding:** all-MiniLM-L6-v2
- **Vector DB:** ChromaDB (local)
""")

    st.markdown("### ⚡ Quick Commands")
    st.code("python3 -m ingestion.run_ingestion", language="bash")
    st.code("streamlit run ui/app.py", language="bash")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.75rem;color:#9aa0a6'>"
        "Data sourced from official public pages only.<br>"
        "No third-party blogs or unofficial sources."
        "</div>",
        unsafe_allow_html=True,
    )

# ============================================================
# MAIN HEADER
# ============================================================
st.markdown('<p class="main-title">📊 SBI MF FAQ Assistant</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="main-subtitle">Facts-only answers from official SBI MF, SEBI & AMFI sources. '
    'No investment advice.</p>',
    unsafe_allow_html=True,
)

# ============================================================
# EXAMPLE QUESTION CHIPS
# ============================================================
st.markdown("**💡 Try asking:**")
col1, col2, col3 = st.columns(3)

EXAMPLE_QUESTIONS = {
    "col1": "What is the expense ratio of SBI Blue Chip Fund?",
    "col2": "What is the ELSS lock-in period?",
    "col3": "How do I download my capital-gains statement?",
}

with col1:
    if st.button("Expense ratio of SBI Blue Chip Fund?", key="ex1"):
        st.session_state["prefill"] = EXAMPLE_QUESTIONS["col1"]
with col2:
    if st.button("ELSS lock-in period?", key="ex2"):
        st.session_state["prefill"] = EXAMPLE_QUESTIONS["col2"]
with col3:
    if st.button("Download capital-gains statement?", key="ex3"):
        st.session_state["prefill"] = EXAMPLE_QUESTIONS["col3"]

st.markdown("---")

# ============================================================
# SESSION STATE INIT
# ============================================================
if "history" not in st.session_state:
    st.session_state["history"] = []

# ============================================================
# RENDER EXISTING CHAT HISTORY
# ============================================================
for msg in st.session_state["history"]:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "source_card":
            # Re-render rich source card for assistant answers
            st.markdown(msg["answer"])
            st.markdown(
                f'<div class="source-card">'
                f'📎 <b>Source:</b> <a href="{msg["source_url"]}" target="_blank">{msg["source_url"]}</a><br>'
                f'🗓️ <b>Last updated from sources:</b> {msg["last_fetched_date"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif msg.get("type") == "refusal":
            st.markdown(
                f'<div class="refusal-box">ℹ️ {msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(msg["content"])

# ============================================================
# CHAT INPUT
# ============================================================
prefill = st.session_state.pop("prefill", "")
query   = st.chat_input("Ask a factual question about SBI MF schemes…")

# Example button prefill takes priority
if prefill:
    query = prefill

# ============================================================
# PROCESS QUERY
# ============================================================
if query:
    # Display user message
    st.session_state["history"].append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Call pipeline
    with st.chat_message("assistant"):
        with st.spinner("Looking up official sources…"):
            result = answer(query)

        if not result.get("allowed"):
            # Guardrail refused — show styled notice
            msg_text = result.get("message", "I can only answer factual questions.")
            st.markdown(
                f'<div class="refusal-box">ℹ️ {msg_text}</div>',
                unsafe_allow_html=True,
            )
            st.session_state["history"].append({
                "role":    "assistant",
                "type":    "refusal",
                "content": msg_text,
            })

        else:
            # Factual answer — show answer + source card
            answer_text       = result.get("answer", "")
            source_url        = result.get("source_url", "")
            last_fetched_date = result.get("last_fetched_date", "")

            st.markdown(answer_text)

            if source_url:
                st.markdown(
                    f'<div class="source-card">'
                    f'📎 <b>Source:</b> <a href="{source_url}" target="_blank">{source_url}</a><br>'
                    f'🗓️ <b>Last updated from sources:</b> {last_fetched_date}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.session_state["history"].append({
                "role":             "assistant",
                "type":             "source_card",
                "answer":           answer_text,
                "source_url":       source_url,
                "last_fetched_date": last_fetched_date,
            })

# ============================================================
# DISCLAIMER FOOTER
# ============================================================
st.markdown(
    '<div class="disclaimer">'
    '⚠️ <b>Disclaimer:</b> This assistant provides factual information only from official '
    'SBI MF, SEBI, and AMFI public sources. It does not provide investment advice, '
    'recommend schemes, or compute fund performance. '
    'For investment decisions, consult a SEBI-registered investment advisor.'
    '</div>',
    unsafe_allow_html=True,
)
