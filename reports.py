"""Render saved repair evidence into a portable Markdown report."""
import json


def markdown(events):
    results = [event for event in events if event["event"] in ("result", "rejected")]
    result = results[-1] if results else {}
    terminal = events[-1]["event"] if events else "missing"
    outcome = "Verified" if terminal == "result" else "Unverified"
    lines = ["# VersionBridge repair evidence", "", f"Outcome — {outcome}", "",
             f"Run — {result.get('id', 'unavailable')}",
             f"Verification scope — {result.get('verification_scope', 'Existing repository tests; controlled profile policy')}",
             f"Human decision — {result.get('human_decision', 'pending maintainer review')}",
             f"Diagnostic categories — {', '.join(result.get('classification', {}).get('categories', ['not recorded']))}",
             f"Independent checks — {json.dumps(result.get('independent_checks', {'status': 'not recorded for this profile'}))}",
             f"Source SHA — {result.get('source_sha', 'not recorded by legacy profile')}",
             f"Runtime image — {result.get('image_digest', 'inspect sandbox events')}",
             f"Source commit — {result.get('commit') or 'bundled fixture'}",
             f"Provider — {result.get('provider', 'unavailable')}",
             f"Patch SHA-256 — {result.get('patch_sha256', 'unavailable')}",
             f"Test SHA-256 — {result.get('tests_sha256', 'unavailable')}", "",
             "## Test comparison", "", "| Test | Before | After |", "| --- | --- | --- |"]
    before, after = result.get("baseline_tests", {}), result.get("verification_tests", {})
    for name in sorted(before.keys() | after.keys()):
        label = name.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {label} | {before.get(name, 'missing')} | {after.get(name, 'missing')} |")
    lines.extend(["", "## Recorded events", "",
                  "The following JSON contains source data from the run. Imported results depend on the supplied tests.", ""])
    payload = json.dumps(events, indent=2)
    longest = max((len(part) - len(part.lstrip("~")) for part in payload.splitlines()), default=0)
    fence = "~" * max(4, longest + 1)
    lines.extend([fence + "json", payload, fence, ""])
    return "\n".join(lines)
