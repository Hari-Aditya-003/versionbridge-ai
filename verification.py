"""Interpret the bounded test report supplied by the Python adapter."""
import json

PYTEST_COMMAND = ["python", "-I", "/opt/versionbridge/pytest_runner.py"]
REPORT_PREFIX = "VERSIONBRIDGE_TEST_REPORT "
REPORT_WINDOW = 800_000


def parse_report(output_tail):
    lines = output_tail.decode(errors="replace").rstrip().split("\n")
    if not lines[-1].startswith(REPORT_PREFIX):
        return {}
    try:
        report = json.loads(lines[-1][len(REPORT_PREFIX):])
    except (ValueError, RecursionError):
        return {}
    if (not isinstance(report, dict) or len(report) > 512
            or any(not node_id or len(node_id) > 256
                   or outcome not in ("passed", "failed", "skipped")
                   for node_id, outcome in report.items())):
        return {}
    return report


def verification_failure(baseline, candidate):
    if not candidate:
        return "The verification test report was missing, incomplete, or invalid."
    if baseline.keys() != candidate.keys():
        return "The collected test inventory changed."
    if any((before == "skipped") != (candidate[node_id] == "skipped")
           for node_id, before in baseline.items()):
        return "The set of skipped or expected-failure tests changed."
    if "failed" in candidate.values() or "passed" not in candidate.values():
        return "The verification suite did not pass."
    return None
