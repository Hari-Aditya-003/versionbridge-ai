"""Run the complete Docker acceptance suite without spending inference credits."""
import hashlib
import io
import json
import re
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from arithmetic import candidate_expressions, examples
from profiles import PROFILES
from inference import Proposal, propose, validate_replacement
from server import containment, patch_diff, repair
from python_target import resolve_target


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

    def test_invoice_sample(self):
        events = []
        repair(record(events), "invoice", profile_id="billing")
        result = events[-1]
        self.assertEqual(result["event"], "result")
        self.assertIn("4 failed", result["before"])
        self.assertIn("4 passed", result["after"])
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

    def test_scoped_python_import_runs_real_tests(self):
        revision = "a" * 40

        def copy_snapshot(_repository, _ref, project):
            (project / "maths.py").write_text("def discount(price, reduction):\n    return price + reduction\n")
            (project / "test_maths.py").write_text(
                "from maths import discount\n\ndef test_discount():\n    assert discount(10, 2) == 8\n"
            )
            return revision

        def candidate(profile, log, code, previous):
            self.assertIn("test_discount", log)
            line = validate_replacement(profile, {"replacement": "return price - reduction",
                                                  "diagnosis": "Subtract the reduction."})
            return Proposal(line, "Transport test double", "Subtract the reduction.", {"test": True})

        events = []
        with patch.dict("os.environ", {"ENABLE_SCOPED_REPAIR": "1", "ENABLE_PUBLIC_IMPORT": "1",
                                       "VERSIONBRIDGE_INFERENCE_MODE": "local-gpu"}):
            with patch("server.snapshot", side_effect=copy_snapshot), patch("server.propose", side_effect=candidate):
                repair(record(events), "scoped", "https://github.com/example/project", "", "python",
                       "maths.py", "discount")
        self.assertEqual(events[-1]["commit"], revision)
        self.assertIn("1 failed", events[-1]["before"])
        self.assertIn("1 passed", events[-1]["after"])
        self.assert_cleanup(events, 2)

    def test_scoped_target_rejects_tests_and_ambiguous_bodies(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / "maths.py").write_text("def f(x):\n    y = x\n    return y\n")
            for filename in ("../maths.py", "tests/helpers.py", "conftest.py", "maths.py"):
                with self.subTest(filename=filename), self.assertRaises(RuntimeError):
                    resolve_target(project, filename, "f")

    def test_python_target_uses_physical_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / "maths.py").write_text(
                '"""one\u2028two\u2028three\u2028four"""\n\n'
                'def donor(x):\n    return x + 1\n\ndef target(x):\n    return x + 2\n'
            )
            _, _, profile, line = resolve_target(project, "maths.py", "target")
        self.assertEqual((profile.original, line), ("    return x + 2", 7))

    def test_patch_download_applies_to_crlf_and_unterminated_files(self):
        for separator, end in (("\r\n", "\r\n"), ("\n", ""), ("\r\n", "")):
            with self.subTest(separator=separator, end=end), tempfile.TemporaryDirectory() as folder:
                original = separator.join(("def f(x):", "    return x + 1")) + end
                patched = original.replace("x + 1", "x - 1")
                (Path(folder) / "maths.py").write_bytes(original.encode())
                result = subprocess.run(
                    ["git", "apply", "--check"], input=patch_diff(original, patched, "maths.py").encode(),
                    cwd=folder, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_local_mode_never_replaces_required_vultr(self):
        with patch.dict("os.environ", {"VERSIONBRIDGE_INFERENCE_MODE": "local-gpu", "REQUIRE_INFERENCE": "1"}):
            with self.assertRaisesRegex(RuntimeError, "requires Vultr"):
                propose(PROFILES["billing"], "failure", "source")

    def test_arithmetic_candidates_follow_observed_values(self):
        output = "\n".join(
            f"E   assert {actual} == {expected}\nE    +  where {actual} = total({args})"
            for actual, expected, args in ((153, 400, "125, 3, 25"), (150, 25, "125, 0, 25"),
                                           (126, 125, "125, 1, 0"), (28, 25, "0, 3, 25"))
        )
        observations = examples(output)
        self.assertEqual(examples("E   assert 400 == 153\nE    +  where 153 = total(125, 3, 25)"),
                         [("153", "400", "total", "125, 3, 25")])
        self.assertFalse(examples("E   assert 400 == 153\nE    +  where 99 = total(125, 3, 25)"))
        names = ("unit", "quantity", "fee")
        self.assertIn("return (unit * quantity) + fee",
                      candidate_expressions(names, "def total(unit, quantity, fee):", observations))
        self.assertEqual(candidate_expressions(names, "def unrelated(unit, quantity, fee):", observations), ())

    def test_local_chat_transport_budget(self):
        response = {"done": True, "model": "fixture", "eval_count": 25,
                    "message": {"content": json.dumps({
                        "diagnosis": "Apply the fee.", "replacement": "return unit_cents * quantity + fee_cents",
                    })}}
        with patch.dict("os.environ", {"VERSIONBRIDGE_INFERENCE_MODE": "local-gpu"}, clear=True):
            with patch("local_gpu.http.client.HTTPConnection") as connection:
                http = connection.return_value
                http.getresponse.return_value.status = 200
                http.getresponse.return_value.read.return_value = json.dumps(response).encode()
                proposal = propose(PROFILES["billing"], "failure", "source")
        self.assertEqual(connection.call_args.args, ("127.0.0.1", 11434))
        method, path, body, _headers = http.request.call_args.args
        self.assertEqual((method, path), ("POST", "/api/chat"))
        request = json.loads(body)
        self.assertEqual(request["keep_alive"], 0)
        self.assertEqual(request["options"]["num_ctx"], 2048)
        self.assertEqual(request["format"]["required"], ["diagnosis", "replacement"])
        self.assertFalse(request["format"]["additionalProperties"])
        self.assertEqual(proposal.receipt["accelerator"], "unverified")
        http.close.assert_called_once()

    def assert_cleanup(self, events, count):
        sandboxes = [event for event in events if event["event"] == "sandbox"]
        self.assertEqual([event["status"] for event in sandboxes], ["Dispatching", "Removed"] * count)
        self.assertEqual(len({event["name"] for event in sandboxes}), count)
        self.assertTrue(all(re.fullmatch(r"versionbridge-[a-f0-9]{32}", event["name"]) for event in sandboxes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
