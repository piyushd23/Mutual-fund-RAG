# ingestion/run_ingestion.py
# Phase 2: Orchestrator — loads all 25 official sources, chunks, embeds,
# and stores everything in ChromaDB. Run this once before starting the UI.
#
# Usage:
#   python -m ingestion.run_ingestion
#
# Progress is printed to stdout. Errors per URL are caught and logged so
# a single failed URL does not abort the whole run.

import sys
from ingestion.loader   import load_source
from ingestion.chunker  import chunk_document
from ingestion.embedder import embed_texts
from ingestion.store    import upsert_chunks, collection_count

# ---------------------------------------------------------------------------
# All 25 official source URLs (from data/sources.md)
# ---------------------------------------------------------------------------
SOURCES = [
    # -- AMC Scheme Documents (SID / KIM / Factsheet) ----------------------
    "https://www.sbimf.com/docs/default-source/lists/kim---sbi-blue-chip-fund.pdf?sfvrsn=95255f2a_0",
    "https://www.sbimf.com/docs/default-source/lists/sid---sbi-bluechip-fund.pdf?sfvrsn=bbe1a4ba_0",
    "https://www.sbimf.com/offer-document-sid-kim",
    "https://www.sbimf.com/sid-kim-archive",
    "https://www.sbimf.com/factsheets",
    "https://www.sbimf.com/portfolios",
    "https://www.sbimf.com/docs/default-source/documents/statement-of-additional-information.pdf",
    "https://www.sbimf.com/docs/default-source/pdf/equity-schemes---scheme-differentiation.pdf",

    # -- Fees / Charges / TER -----------------------------------------------
    "https://www.sbimf.com/total-expense-ratio",
    "https://www.sbimf.com/forms",

    # -- Riskometer / Benchmark ---------------------------------------------
    "https://www.sbimf.com/docs/default-source/pdf/index-funds---scheme-differentiation.pdf",
    "https://www.sebi.gov.in/legal/circulars/oct-2020/circular-on-product-labeling-in-mutual-fund-schemes-risk-o-meter_47796.html",
    "https://www.sebi.gov.in/sebi_data/attachdocs/oct-2020/1602580413614.pdf",
    "https://www.sebi.gov.in/sebi_data/attachdocs/1430388883147.pdf",
    "https://compfie.aparajitha.com/wp-content/uploads/2021/09/02092021_FCC_03.pdf",

    # -- Scheme FAQs / Investor Education -----------------------------------
    "https://www.sbimf.com/faq",
    "https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified",
    "https://www.sbimf.com/investment-options",

    # -- Statement / Tax-Document Guides ------------------------------------
    "https://www.sbimf.com/kyc-procedure",
    "https://online.sbimf.com/statement",
    "https://www.sbimf.com/idcw-history",
    "https://www.sbimf.com/grievance-redressal",

    # -- SEBI / AMFI Regulatory Layer ---------------------------------------
    "https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf",
    "https://www.amfiindia.com/",
    "https://www.amfiindia.com/investor",

    # -- New specific additions for missing questions -----------------------
    "https://www.sbimf.com/en-us/mutual-fund/sbi-long-term-equity-fund",
    "https://www.sbimf.com/en-us/mutual-fund/sbi-small-cap-fund",
    "https://www.sbimf.com/en-us/investor-corner/capital-gains-statement",
]


def run(sources: list[str] = SOURCES) -> None:
    """
    Full ingestion pipeline:
      For each URL → load → chunk → (batch) embed → upsert into ChromaDB.
    """
    print("=" * 60)
    print("MF FAQ RAG Chatbot — Data Ingestion")
    print(f"Total sources to process: {len(sources)}")
    print("=" * 60)

    all_chunks: list[dict] = []
    failed: list[str] = []

    for i, url in enumerate(sources, 1):
        print(f"\n[{i}/{len(sources)}] {url}")
        try:
            docs = load_source(url)
            url_chunks = []
            for doc in docs:
                url_chunks.extend(chunk_document(doc))
            print(f"  → {len(url_chunks)} chunks produced")
            all_chunks.extend(url_chunks)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            failed.append(url)

    print("\n" + "=" * 60)
    print(f"Total chunks to embed: {len(all_chunks)}")

    if not all_chunks:
        print("No chunks produced. Aborting.")
        return

    # Embed all chunks in one batched call
    print("Embedding chunks (this may take a few minutes)...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)

    # Upsert into ChromaDB
    print("Storing in ChromaDB...")
    upsert_chunks(all_chunks, embeddings)

    # Summary
    print("\n" + "=" * 60)
    print(f"Ingestion complete.")
    print(f"  Chunks stored  : {collection_count()}")
    print(f"  Sources failed : {len(failed)}")
    if failed:
        print("  Failed URLs:")
        for url in failed:
            print(f"    - {url}")
    print("=" * 60)


if __name__ == "__main__":
    run()
