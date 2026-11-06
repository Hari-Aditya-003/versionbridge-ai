"""Render saved repair evidence into a portable Markdown report."""

import json


def markdown(events):
    results = [event for event in events if event["event"] in ("result", "rejected")]
    result = results[-1] if results else {}
    terminal = events[-1]["event"] if events else "missing"
    outcome = "Verified" if terminal == "result" else "Unverified"
    lines = [
        "# VersionBridge repair evidence",
        "",
        f"Outcome — {outcome}",
        "",
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
        f"Test SHA-256 — {result.get('tests_sha256', 'unavailable')}",
        "",
        "## Test comparison",
        "",
        "| Test | Before | After |",
        "| --- | --- | --- |",
    ]
    before, after = (
        result.get("baseline_tests", {}),
        result.get("verification_tests", {}),
    )
    for name in sorted(before.keys() | after.keys()):
        label = name.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {label} | {before.get(name, 'missing')} | {after.get(name, 'missing')} |"
        )
    lines.extend(
        [
            "",
            "## Recorded events",
            "",
            "The following JSON contains source data from the run. Imported results depend on the supplied tests.",
            "",
        ]
    )
    payload = json.dumps(events, indent=2)
    longest = max(
        (len(part) - len(part.lstrip("~")) for part in payload.splitlines()), default=0
    )
    fence = "~" * max(4, longest + 1)
    lines.extend([fence + "json", payload, fence, ""])
    return "\n".join(lines)


def plaintext(events, state=None):
    """Portable human-readable scoped files, outputs, changes, and test outcomes."""
    final = next(
        (
            e
            for e in reversed(events)
            if e["event"] in ("result", "rejected", "contained", "error")
        ),
        {},
    )
    streams = {}
    for event in events:
        if event["event"] == "sandbox_output":
            streams[event["name"]] = streams.get(event["name"], "") + event["text"]
    emitted = set()
    lines = [
        "VersionBridge AI - Run bundle",
        "=" * 40,
        "Outcome: "
        + (
            "Verified against listed checks"
            if final.get("event") == "result"
            else (state or final.get("event", "Incomplete")).title()
        ),
        "Run: " + str(final.get("id", "See container identifiers below")),
        "Provider: " + str(final.get("provider", "See execution records")),
        "Review: Maintainer decision required before applying a patch.",
        "",
    ]
    for event in events:
        kind = event["event"]
        if kind == "files":
            lines.extend(["", "FILES / " + event["phase"], event.get("scope", "")])
            for file in event["files"]:
                lines.extend(
                    [
                        "",
                        "--- " + file["path"] + " ---",
                        "SHA-256: " + file["sha256"],
                        file["content"],
                    ]
                )
                if file.get("truncated"):
                    lines.append("[Snapshot truncated by the export allowance]")
        elif kind == "sandbox":
            lines.extend(
                [
                    "",
                    "SANDBOX / " + event["name"],
                    json.dumps(
                        {k: v for k, v in event.items() if k != "event"},
                        ensure_ascii=False,
                    ),
                ]
            )
            if (
                event.get("status") in ("Removed", "Absent")
                and event["name"] in streams
            ):
                lines.extend(["OUTPUT / " + event["name"], streams[event["name"]]])
                emitted.add(event["name"])
        elif kind == "log" and event.get("text", "").strip() not in "".join(
            streams.values()
        ):
            lines.extend(
                [
                    "",
                    "OUTPUT / " + event.get("label", "Execution"),
                    event.get("text", ""),
                ]
            )
        elif kind == "diagnosis":
            lines.extend(
                [
                    "",
                    "MODEL DIAGNOSIS / " + event["provider"],
                    event["text"],
                    json.dumps(event.get("receipt", {})),
                ]
            )
        elif kind in ("result", "rejected"):
            lines.extend(
                [
                    "",
                    "CANDIDATE / " + kind.upper(),
                    event.get("diff", ""),
                    "Rejection reason: " + str(event.get("rejection_reason") or "none"),
                    "Test outcomes: " + json.dumps(event.get("verification_tests", {})),
                    "Independent checks: "
                    + json.dumps(event.get("independent_checks", {})),
                ]
            )
        elif kind in ("error", "contained"):
            lines.append(event.get("message", ""))
    for name, text in streams.items():
        if name not in emitted:
            lines.extend(["", "OUTPUT / " + name, text])
    return "\n".join(lines) + "\n"
