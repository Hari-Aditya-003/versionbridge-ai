"""Run the complete Docker acceptance suite without spending inference credits."""
import hashlib
import re
import unittest

from profiles import PROFILES
from server import containment, repair, validate_replacement


def record(events):
    return lambda name, data: events.append({"event": name, **data})


class AcceptanceTests(unittest.TestCase):
    def test_two_supported_migrations(self):
        for profile in ("pandas", "settings"):
            with self.subTest(profile=profile):
                events = []
                repair(record(events), profile, profile_id=profile)
                report = events[-1]
                self.assertEqual(report["event"], "result")
                self.assertIn("2 failed", report["before"])
                self.assertIn("2 passed", report["after"])
                self.assertEqual((report["baseline_exit_code"], report["verification_exit_code"]), (1, 0))
                self.assertEqual(hashlib.sha256(report["diff"].encode()).hexdigest(), report["patch_sha256"])
                self.assert_cleanup(events, 2)

    def test_reject_regression(self):
        events = []
        with self.assertRaisesRegex(RuntimeError, "Candidate rejected"):
            repair(record(events), "rejected", profile_id="regression")
        report = events[-1]
        self.assertEqual(report["event"], "rejected")
        self.assertIn("FAILED test_regression_pipeline.py::test_standard_frame_migration", report["before"])
        self.assertNotIn("FAILED test_regression_pipeline.py::test_preserve_adapter_audit_metadata", report["before"])
        self.assertIn("FAILED test_regression_pipeline.py::test_preserve_adapter_audit_metadata", report["after"])
        self.assertIn("1 failed, 1 passed", report["after"])
        self.assertFalse(any(event["event"] == "result" for event in events))
        self.assert_cleanup(events, 2)

    def test_containment(self):
        events = []
        containment(record(events))
        self.assertEqual(events[-1]["event"], "contained")
        self.assertTrue(any(event.get("timed_out") and event["status"] == "Removed" for event in events))
        self.assert_cleanup(events, 3)

    def test_model_output_validation(self):
        profile = PROFILES["settings"]
        for output in ({}, [], {"replacement": 1}, {"replacement": "import os"},
                       {"replacement": profile.candidates[0] + "\nimport os"}):
            with self.subTest(output=output), self.assertRaises(ValueError):
                validate_replacement(profile, output)
        self.assertEqual(validate_replacement(profile, {"replacement": profile.candidates[0]}),
                         profile.candidates[0])

    def assert_cleanup(self, events, count):
        sandboxes = [event for event in events if event["event"] == "sandbox"]
        self.assertEqual([event["status"] for event in sandboxes], ["Dispatching", "Removed"] * count)
        self.assertEqual(len({event["name"] for event in sandboxes}), count)
        self.assertTrue(all(re.fullmatch(r"versionbridge-[a-f0-9]{32}", event["name"]) for event in sandboxes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
