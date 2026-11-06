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

import budget
import gpu_guard
import history
import jobs
from arithmetic import candidate_expressions, examples
from profiles import PROFILES, Profile
from projects import is_pinned_example, PINNED_REPOSITORY, PINNED_REVISION, snapshot
from inspection import inspect_project
from inference import Proposal, propose, validate_replacement
from server import containment, patch_diff, repair
from python_target import resolve_target


def record(events):
    return lambda name, data: events.append({"event": name, **data})


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        database = patch.object(history, "DB", Path(folder.name) / "test.sqlite3")
        database.start()
        self.addCleanup(database.stop)

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

    def test_bundled_beta_repairs(self):
        for profile, count in (("go", 4), ("rust", 4), ("java", 4), ("cpp", 4), ("postgresql", 4), ("typescript", 4), ("javascript", 4), ("sqlite", 4), ("algorithm", 5)):
            with self.subTest(profile=profile):
                events = []
                repair(record(events), profile, profile_id=profile)
                report = events[-1]
                self.assertEqual(report["event"], "result")
                self.assertIn("failed", report["baseline_tests"].values())
                self.assertEqual(list(report["verification_tests"].values()), ["passed"] * count)
                self.assert_cleanup(events, 2)

    def test_reject_patch_that_turns_failure_into_skip(self):
        events = []
        profile = Profile("Test integrity", "", "FLAG = 0", ("FLAG = 1",), "test_feature")

        def snapshot(repository, ref, folder):
            (folder / "feature.py").write_text("FLAG = 0\n")
            (folder / "test_feature.py").write_text(
                "import pytest\nfrom feature import FLAG\n"
                "def test_feature():\n    if FLAG:\n        pytest.skip('feature disabled')\n"
                "    assert False\ndef test_unrelated():\n    assert True\n"
            )
            return "a" * 40

        with patch.dict(PROFILES, {"skip_guard": profile}), patch("server.snapshot", snapshot):
            with patch.dict("os.environ", {"ENABLE_PUBLIC_IMPORT": "1"}):
                with self.assertRaisesRegex(RuntimeError, "Candidate rejected"):
                    repair(record(events), "skip", repository="example", profile_id="skip_guard")
        rejected = events[-1]
        self.assertEqual(rejected["verification_exit_code"], 0)
        self.assertEqual(rejected["event"], "rejected")
        self.assertIn("skipped", rejected["rejection_reason"])
        self.assert_cleanup(events, 2)

    def test_queue_cancel_and_restart(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(history, "DB", Path(folder) / "runs.db"):
            running = jobs.submit(["run"])
            queued = jobs.submit(["queued"])
            cancelled = jobs.submit(["cancel"])
            self.assertEqual(jobs.claim(), (running, ["run"]))
            jobs.publish(running, [{"event": "stage"}])
            self.assertTrue(jobs.cancel(cancelled))
            jobs.interrupted()
            self.assertEqual(jobs.get(running, 0)["state"], "interrupted")
            self.assertEqual(jobs.get(running, 1)["events"], [])
            self.assertEqual(jobs.get(cancelled, 0)["state"], "cancelled")
            self.assertEqual(jobs.claim(), (queued, ["queued"]))
            self.assertTrue(jobs.cancel(queued))
            jobs.publish(queued, [{"event": "result"}], project="Test")
            self.assertEqual(jobs.get(queued, 0)["state"], "cancelled")
            self.assertEqual(history.recent(), [])

    def test_paid_inference_reservation_rejects_before_transport(self):
        with patch.dict("os.environ", {"INFERENCE_BUDGET_USD": "0", "VULTR_API_KEY": "fixture-key",
                                       "VULTR_MODEL": "fixture-model"}):
            with patch("inference.urlopen") as transport:
                with self.assertRaises(budget.BudgetExceeded):
                    propose(PROFILES["billing"], "failure", "source")
                transport.assert_not_called()

    def test_queue_idempotency_and_budget_persistence(self):
        settings = ["", "", "billing", "", ""]
        first = jobs.submit(settings, "request-key-123456")
        self.assertEqual(jobs.submit(settings, "request-key-123456"), first)
        with self.assertRaises(ValueError):
            jobs.submit(["different"], "request-key-123456")
        with patch.dict("os.environ", {"INFERENCE_BUDGET_USD": "1", "INFERENCE_DAILY_REQUESTS": "1"}):
            budget.reserve(1000, 700)
            self.assertEqual(budget.status()["requests_today"], 1)
            with self.assertRaises(budget.BudgetExceeded):
                budget.reserve(1000, 700)

    def test_gpu_quiet_mode_pauses_on_busy_or_stale_metrics(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "gpu.json"
            telemetry = {"timestamp": time.time(), "temperature_c": 50, "memory_total_mb": 4096,
                         "memory_used_mb": 500, "utilization_percent": 0}
            filename.write_text(json.dumps(telemetry))
            with patch.dict("os.environ", {"VERSIONBRIDGE_GPU_STATUS_FILE": str(filename)}):
                gpu_guard.check()
                for changes in ({"temperature_c": 70}, {"utilization_percent": 90}, {"timestamp": 0},
                                {"memory_used_mb": 4000}):
                    filename.write_text(json.dumps({**telemetry, **changes}))
                    with self.assertRaises(RuntimeError):
                        gpu_guard.check()

    def test_public_repository_allowlist_is_exact(self):
        self.assertTrue(is_pinned_example(PINNED_REPOSITORY, PINNED_REVISION, "pandas"))
        for repository, ref, profile in (
            (PINNED_REPOSITORY, "main", "pandas"),
            (PINNED_REPOSITORY + ".git", PINNED_REVISION, "pandas"),
            (PINNED_REPOSITORY, PINNED_REVISION, "python"),
        ):
            self.assertFalse(is_pinned_example(repository, ref, profile))

    def test_snapshot_rejects_archive_traversal_and_links(self):
        from zipfile import ZipFile, ZipInfo
        for name, mode in (("root/../../escape.py", 0), ("root/link.py", 0o120777 << 16)):
            with self.subTest(path=name), tempfile.TemporaryDirectory() as folder:
                archive = io.BytesIO()
                with ZipFile(archive, "w") as output:
                    member = ZipInfo(name)
                    member.external_attr = mode
                    output.writestr(member, "outside")
                with patch("projects.fetch", side_effect=[
                    json.dumps({"sha": PINNED_REVISION}).encode(), archive.getvalue(),
                ]):
                    with self.assertRaisesRegex(RuntimeError, "archive path"):
                        snapshot(PINNED_REPOSITORY, PINNED_REVISION, Path(folder))

    def test_static_inventory_rejects_nested_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / "package.json").write_text("[" * 2000 + "0" + "]" * 2000)
            inventory = inspect_project(project)
            self.assertEqual(inventory["manifests"][0]["error"], "Invalid package metadata")

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
        self.assertGreater(proposal.receipt.pop("budget")["reserved_usd"], 0)
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
