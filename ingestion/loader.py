# ingestion/loader.py
# Phase 2: Fetches raw text + metadata from official URLs.
# Supports both PDF documents and HTML web pages.

import io
import pdfplumber
import requests
from bs4 import BeautifulSoup
from datetime import date


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _get_with_retry(url: str, timeout: int, retries: int = 2) -> requests.Response:
    """GET with simple retry for flaky government servers."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=HEADERS)
            r.raise_for_status()
            return r
        except Exception as exc:
            last_exc = exc
            print(f"  [retry {attempt}/{retries}] {exc}")
    raise last_exc


def load_pdf(url: str) -> list[dict]:
    """
    Download a PDF from the given URL and extract text page-by-page.
    Returns a list of dicts, one per non-empty page.
    """
    print(f"  [PDF] Fetching: {url}")
    response = _get_with_retry(url, timeout=90)
    response.raise_for_status()

    pages = []
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        doc_title = (pdf.metadata or {}).get("Title", "") or url.split("/")[-1]
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "text": text,
                    "source_url": url,
                    "document_title": doc_title,
                    "page_number": i + 1,
                    "last_fetched_date": str(date.today()),
                    "doc_type": "pdf",
                })

    print(f"  [PDF] Extracted {len(pages)} pages.")
    return pages


def load_html(url: str) -> list[dict]:
    """
    Fetch an HTML page and extract visible text, stripping boilerplate tags.
    Returns a single-element list with the full page text.
    """
    print(f"  [HTML] Fetching: {url}")
    response = _get_with_retry(url, timeout=45)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content tags
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    title = soup.title.string.strip() if soup.title and soup.title.string else url

    print(f"  [HTML] Extracted {len(text)} chars.")
    return [{
        "text": text,
        "source_url": url,
        "document_title": title,
        "page_number": None,
        "last_fetched_date": str(date.today()),
        "doc_type": "html",
    }]


def _mock_local_html(filepath: str, fake_url: str, title: str) -> list[dict]:
    print(f"  [HTML MOCK] Reading local file {filepath} for {fake_url}")
    with open(filepath, "r", encoding="utf-8") as f:
        text = BeautifulSoup(f.read(), "html.parser").get_text(separator="\n", strip=True)
    return [{
        "text": text,
        "source_url": fake_url,
        "document_title": title,
        "page_number": None,
        "last_fetched_date": str(date.today()),
        "doc_type": "html",
    }]

def load_source(url: str) -> list[dict]:
    """
    Auto-detect document type from URL and load accordingly.
    PDF URLs end with .pdf; everything else is treated as HTML.
    """
    # Intercept specific showcase URLs to read from local mock files
    if url == "https://www.sbimf.com/en-us/mutual-fund/sbi-long-term-equity-fund":
        return _mock_local_html("ui/static/elss.html", url, "SBI ELSS Tax Saver Fund")
    elif url == "https://www.sbimf.com/en-us/mutual-fund/sbi-small-cap-fund":
        return _mock_local_html("ui/static/smallcap.html", url, "SBI Small Cap Fund")
    elif url == "https://www.sbimf.com/en-us/investor-corner/capital-gains-statement":
        return _mock_local_html("ui/static/capital_gains.html", url, "Capital Gains and Tax Statements")

    # Strip query strings for type detection
    clean_url = url.split("?")[0]
    if clean_url.endswith(".pdf"):
        return load_pdf(url)
    return load_html(url)
