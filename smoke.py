"""Run the complete Docker acceptance suite without spending inference credits."""
import hashlib
import io
import json
import re
import unittest
from unittest.mock import patch

from profiles import PROFILES
from inference import Proposal, propose, validate_replacement
from server import containment, repair


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
        profile = PROFILES["billing"]
        for line in ("return __import__('os')", "return unit_cents.real", "return unit_cents ** 8",
                     "return unit_cents\nimport os", "return unknown + 1"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                validate_replacement(profile, {"replacement": line, "diagnosis": "test"})
        self.assertEqual(validate_replacement(profile, {
            "replacement": "return fee_cents + (quantity * unit_cents)", "diagnosis": "Multiply first",
        }), "    return fee_cents + quantity * unit_cents")

    def test_vultr_response_receipt(self):
        response = {"id": "test-receipt", "model": "served-model", "usage": {"total_tokens": 123},
                    "choices": [{"message": {"content": json.dumps({
                        "diagnosis": "Multiply the unit price by quantity.",
                        "replacement": "return quantity * unit_cents + fee_cents",
                    })}}]}
        with patch.dict("os.environ", {"VULTR_API_KEY": "fixture-key", "VULTR_MODEL": "fixture-model"}):
            with patch("inference.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as transport:
                proposal = propose(PROFILES["billing"], "failing test", "source")
        self.assertEqual(transport.call_args.args[0].full_url,
                         "https://api.vultrinference.com/v1/chat/completions")
        self.assertEqual(proposal.receipt, {"requested_model": "fixture-model", "served_model": "served-model",
                                           "completion_id": "test-receipt", "tokens": {"total_tokens": 123}})

    def test_model_style_feedback_retries_in_fresh_containers(self):
        events = []
        first = Proposal("    return unit_cents * quantity", "Test double", "Multiply quantity", {"test": True})
        second = Proposal("    return fee_cents + quantity * unit_cents", "Test double",
                          "Restore the flat fee", {"test": True})
        with patch("server.propose", side_effect=[first, second]) as model:
            repair(record(events), "retry", profile_id="billing")
        self.assertEqual(events[-1]["event"], "result")
        self.assertEqual(events[-1]["attempt"], 2)
        self.assertIn("4 passed", events[-1]["after"])
        self.assertIn("failed", model.call_args.args[3]["failure"])
        self.assertEqual(len([event for event in events if event["event"] == "rejected"]), 1)
        self.assert_cleanup(events, 3)

    def assert_cleanup(self, events, count):
        sandboxes = [event for event in events if event["event"] == "sandbox"]
        self.assertEqual([event["status"] for event in sandboxes], ["Dispatching", "Removed"] * count)
        self.assertEqual(len({event["name"] for event in sandboxes}), count)
        self.assertTrue(all(re.fullmatch(r"versionbridge-[a-f0-9]{32}", event["name"]) for event in sandboxes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
