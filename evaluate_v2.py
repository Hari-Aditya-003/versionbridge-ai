"""Evaluate no-enum migrations separately from V1 fixture-replacement results."""

import argparse
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

from evaluation_scoreboard import summarize
from v2_pipeline import run, RepairFailure
from v2_tasks import TASKS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--attempts", type=int, choices=[1, 2], default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    models = args.models or [os.getenv("VULTR_MODEL", "glm-5.3-flash")]
    if not 1 <= len(models) <= 2:
        parser.error("Evaluate one or two registered models.")
    records = []
    runs = []
    for model in models:
        for task in TASKS:
            events = []
            with patch.dict(os.environ, {"VULTR_MODEL": model, "VULTR_MODEL_POOL": ""}):
                try:
                    run(
                        lambda name, data: events.append({"event": name, **data}),
                        f"eval-{time.time_ns()}",
                        task,
                        args.attempts,
                    )
                except RepairFailure as exc:
                    events.append(
                        {"event": "error", "message": str(exc), "outcome": exc.outcome}
                    )
            results = [e for e in events if e["event"] in ("result", "rejected")]
            result = results[-1] if results else {}
            receipts = [
                e.get("receipt", {}) for e in events if e["event"] == "diagnosis"
            ]
            categories = result.get("classification", {}).get("categories", ["unknown"])
            for category in categories:
                records.append(
                    {
                        "task": task,
                        "category": category,
                        "model": model,
                        "served_models": [r.get("served_model") for r in receipts],
                        "eligible": events[-1]["event"] == "result",
                        "independent_pass": result.get("independent_checks", {}).get(
                            "passed"
                        ),
                        "latency_ms": result.get("elapsed_ms", 0),
                        "reserved_usd": sum(
                            r.get("budget", {}).get("reserved_usd", 0) for r in receipts
                        ),
                    }
                )
            runs.append({"task": task, "requested_model": model, "events": events})
    report = {
        "schema_version": 1,
        "suite": "controlled no-enum migration holdouts",
        "seed": 7319,
        "limitations": "Three constructed API migration tasks, not a representative unseen-repository accuracy benchmark.",
        "records": records,
        "scoreboard": summarize(records),
        "runs": runs,
    }
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
