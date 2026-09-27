# tests/test_guardrail.py
# Quick smoke tests for the guardrail — no external dependencies needed.
# Run with: python3 -m tests.test_guardrail

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from retrieval.guardrail import check_query

CASES = [
    # (query, expected_allowed, expected_reason_contains)
    ("What is the expense ratio of SBI Blue Chip Fund?", True,  ""),
    ("What is the ELSS lock-in period?",                 True,  ""),
    ("How do I download my capital gains statement?",    True,  ""),
    ("My PAN is ABCDE1234F, what are my holdings?",      False, "pii"),
    ("Should I invest in SBI Bluechip Fund?",            False, "advice"),
    ("Which fund gave better returns?",                  False, "performance"),
    ("What is the minimum SIP amount?",                  True,  ""),
    ("recommend a fund for me",                          False, "advice"),
    ("my email is test@example.com",                     False, "pii"),
    ("What is CAGR of this fund?",                       False, "performance"),
]

def run():
    passed = 0
    failed = 0
    print(f"Running {len(CASES)} guardrail tests...\n")
    for query, expect_allowed, expect_reason in CASES:
        result = check_query(query)
        ok = (result.allowed == expect_allowed)
        if expect_reason:
            ok = ok and (result.reason == expect_reason)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        allowed_str = "ALLOW" if result.allowed else f"BLOCK({result.reason})"
        print(f"  [{status}] {allowed_str:20s} | {query[:60]}")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
