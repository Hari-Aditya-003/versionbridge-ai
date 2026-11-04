"""Compare account-approved Vultr model IDs against the three Docker fixtures."""
import json
import os
import sys
import time

from profiles import PROFILES
from server import repair


def evaluate(model):
    os.environ["VULTR_MODEL"] = model
    cases = []
    for profile in PROFILES:
        records = []
        started = time.monotonic()
        try:
            repair(lambda name, data: records.append({"event": name, **data}),
                   "model-eval", profile_id=profile)
        except RuntimeError as exc:
            records.append({"event": "error", "message": str(exc)})
        outcome = next((entry for entry in reversed(records)
                        if entry["event"] in {"result", "rejected"}), None)
        passed = bool(outcome and outcome["provider"].startswith("Vultr Serverless Inference")
                      and outcome["event"] == ("rejected" if profile == "regression" else "result"))
        cases.append({"profile": profile, "expected_outcome": passed,
                      "duration_seconds": round(time.monotonic() - started, 2),
                      "evidence": records})
    return {"model": model, "correct_outcomes": sum(case["expected_outcome"] for case in cases),
            "cases": cases}


if __name__ == "__main__":
    models = list(dict.fromkeys(sys.argv[1:]))
    if not os.getenv("VULTR_API_KEY") or not 1 <= len(models) <= 3:
        raise SystemExit("Set VULTR_API_KEY in the environment and pass 1–3 available Vultr model IDs.")
    results = [evaluate(model) for model in models]
    results.sort(key=lambda item: (-item["correct_outcomes"],
                                  sum(case["duration_seconds"] for case in item["cases"])))
    print(json.dumps(results, indent=2))
    sys.exit(results[0]["correct_outcomes"] != len(PROFILES))
