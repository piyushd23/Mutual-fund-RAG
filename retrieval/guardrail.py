# retrieval/guardrail.py
# Phase 3: Classifies user queries BEFORE any retrieval or LLM call.
# Acts as the first line of defence — blocks PII, advice, and performance queries.

import re

# ---------------------------------------------------------------------------
# Patterns & keywords
# ---------------------------------------------------------------------------

PII_PATTERNS = [
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",               # PAN card (e.g. ABCDE1234F)
    r"\b[2-9][0-9]{11}\b",                        # Aadhaar (12-digit, starts 2-9)
    r"\b[6-9][0-9]{9}\b",                         # Indian mobile (10-digit, starts 6-9)
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",  # Email
    r"\botp\b",                                   # OTP keyword
    r"\bpassword\b",                              # Password keyword
]

ADVICE_KEYWORDS = [
    "should i invest",
    "should i buy",
    "should i sell",
    "recommend",
    "which fund is better",
    "best fund",
    "best scheme",
    "buy or sell",
    "portfolio advice",
    "which scheme should",
    "better option for me",
    "suggest a fund",
    "is it worth investing",
    "should i put money",
]

PERFORMANCE_KEYWORDS = [
    "returns",
    "cagr",
    "profit",
    "which gave more",
    "compare returns",
    "return comparison",
    "compare performance",
    "historical performance",
    "annualised return",
    "past performance",
    "5 year return",
    "10 year return",
]

# Redirect links used in refusal messages
EDUCATIONAL_LINK = (
    "https://www.sbimf.com/learn-about-mutual-funds/mutual-funds-jargons-simplified"
)
FACTSHEET_LINK = "https://www.sbimf.com/factsheets"


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

class GuardrailResult:
    """Holds the outcome of a guardrail check."""

    def __init__(self, allowed: bool, message: str = "", reason: str = ""):
        self.allowed = allowed   # True → proceed to retrieval
        self.message = message   # User-facing refusal message (if not allowed)
        self.reason  = reason    # Internal reason tag for logging


# ---------------------------------------------------------------------------
# Check function
# ---------------------------------------------------------------------------

def check_query(query: str) -> GuardrailResult:
    """
    Run all guardrail checks on the user query.

    Order:
      1. PII detection  (regex-based)
      2. Advice intent  (keyword-based)
      3. Performance    (keyword-based)
      4. Pass           → allowed

    Args:
        query: Raw user input string.

    Returns:
        GuardrailResult with allowed=True (proceed) or allowed=False (refuse).
    """
    q_lower = query.lower()

    # ------------------------------------------------------------------
    # 1. PII check — regex patterns on original (case-sensitive for PAN)
    # ------------------------------------------------------------------
    for pattern in PII_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return GuardrailResult(
                allowed=False,
                reason="pii",
                message=(
                    "⚠️ For your privacy, please do not share personal details such as "
                    "PAN, Aadhaar, phone numbers, email addresses, or OTPs. "
                    "I only answer general factual questions about SBI MF schemes."
                ),
            )

    # ------------------------------------------------------------------
    # 2. Advice / recommendation check
    # ------------------------------------------------------------------
    if any(kw in q_lower for kw in ADVICE_KEYWORDS):
        return GuardrailResult(
            allowed=False,
            reason="advice",
            message=(
                "I can only answer factual questions about mutual fund schemes. "
                "For personalised investment guidance, please consult a "
                "SEBI-registered investment advisor. "
                f"Learn more about MF concepts here: {EDUCATIONAL_LINK}"
            ),
        )

    # ------------------------------------------------------------------
    # 3. Performance / return comparison check
    # ------------------------------------------------------------------
    if any(kw in q_lower for kw in PERFORMANCE_KEYWORDS):
        return GuardrailResult(
            allowed=False,
            reason="performance",
            message=(
                "I don't compute or compare fund returns. "
                "Please refer to the official monthly factsheets for performance data: "
                f"{FACTSHEET_LINK}"
            ),
        )

    # ------------------------------------------------------------------
    # 4. All checks passed
    # ------------------------------------------------------------------
    return GuardrailResult(allowed=True)
