"""Run pytest with a bounded inventory of collected test outcomes."""
import json

import pytest

REPORT_PREFIX = "VERSIONBRIDGE_TEST_REPORT "
MAX_TESTS = 512
MAX_NODE_ID = 256


class Inventory:
    def __init__(self):
        self.outcomes = {}
        self.complete = True

    def pytest_collection_finish(self, session):
        ids = [item.nodeid for item in session.items]
        if (len(ids) > MAX_TESTS or len(set(ids)) != len(ids)
                or any(len(node_id) > MAX_NODE_ID for node_id in ids)):
            self.complete = False
            return
        self.outcomes = dict.fromkeys(ids, "pending")

    def pytest_runtest_logreport(self, report):
        if not self.complete or report.nodeid not in self.outcomes:
            return
        previous = self.outcomes[report.nodeid]
        if report.failed:
            self.outcomes[report.nodeid] = "failed"
        elif previous != "failed":
            if report.skipped or hasattr(report, "wasxfail"):
                self.outcomes[report.nodeid] = "skipped"
            elif report.when == "call" and report.passed and previous == "pending":
                self.outcomes[report.nodeid] = "passed"


if __name__ == "__main__":
    inventory = Inventory()
    status = pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider"], plugins=[inventory])
    report = inventory.outcomes if inventory.complete else {}
    print("\n" + REPORT_PREFIX + json.dumps(report, ensure_ascii=False), flush=True)
    raise SystemExit(status)
