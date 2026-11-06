"""Small version-pinned offline notes. Retrieval never authorizes a patch."""

import re
from collections import Counter
import math

NOTES = [
    {
        "id": "pydantic-settings-v2",
        "package": "pydantic",
        "version_prefix": "2.",
        "text": "Pydantic V2 moved BaseSettings to the separately installed pydantic-settings package. Preserve environment override behavior and field validation.",
        "source_url": "https://docs.pydantic.dev/2.11/migration/",
        "reviewed": "2026-11-06",
        "scope": "Pydantic 2.11",
    },
    {
        "id": "collections-abc-py310",
        "package": "python",
        "version_prefix": "3.",
        "text": "Python 3.10 removed deprecated collections aliases for collections.abc abstract base classes, including Mapping. Check import consumers and preserve mapping behavior.",
        "source_url": "https://docs.python.org/3.12/whatsnew/3.10.html",
        "reviewed": "2026-11-06",
        "scope": "Python 3.10-3.12",
    },
]


def retrieve(query, versions):
    terms = Counter(re.findall(r"[a-z0-9_]+", query.lower()))
    result = []
    for note in NOTES:
        version = versions.get(note["package"], "")
        if not version.startswith(note["version_prefix"]):
            continue
        words = Counter(
            re.findall(r"[a-z0-9_]+", (note["text"] + " " + note["package"]).lower())
        )
        score = sum(
            (words[t] * 2.2 / (words[t] + 1.2))
            * math.log(1 + 2 / (1 + sum(t in n["text"].lower() for n in NOTES)))
            for t in terms
            if words[t]
        )
        if score:
            result.append(
                {
                    **note,
                    "retrieval_score": round(score, 4),
                    "retrieval": "bounded BM25-style lexical ranking",
                }
            )
    return sorted(result, key=lambda n: -n["retrieval_score"])[:3]
