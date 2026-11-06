"""Deterministic multi-label diagnostics; every route retains universal checks."""

import re

RULES = {
    "api": r"ImportError|AttributeError|PydanticImportError|removed API|deprecated|ModuleNotFoundError",
    "algorithm": r"AssertionError|boundary|overflow|assert .*==|wrong total|bisect",
    "type": r"TS\d{4}|error\[E\d+\]|cannot borrow|incompatible types|compiler|javac|compilation",
    "sql": r"SQLSTATE|sqlite3\.|psycopg|missing column|SQL error|paid_orders",
    "security": r"test inventory|skip.*changed|audit|permission denied|unsafe|credential|traversal",
}
GUARDS = [
    "patch_policy",
    "original_test_inventory",
    "independent_checks_when_available",
    "sandbox_cleanup",
]


def classify(failure, path=""):
    text = str(failure)[:18000]
    matches = []
    for category, pattern in RULES.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matches.append(
                {
                    "category": category,
                    "evidence": match[0][:160],
                    "path": str(path)[:180],
                    "basis": "deterministic_signature",
                }
            )
    return {
        "categories": [m["category"] for m in matches] or ["unknown"],
        "matches": matches,
        "confidence_source": "matched signatures"
        if matches
        else "insufficient diagnostic evidence",
        "universal_guards": GUARDS,
        "narrow_scope": not matches,
    }
