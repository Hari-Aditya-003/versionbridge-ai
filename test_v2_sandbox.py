"""Real Docker V2 checks with explicit transport doubles, not answer-key prompts."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import history


class V2SandboxTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        p = patch.object(history, "DB", Path(temp.name) / "runs.sqlite3")
        p.start()
        self.addCleanup(p.stop)

    def generate(self, request):
        from providers.base import ModelResponse

        data = json.loads(request.messages[-1]["content"])
        edits = []
        for item in data["context"]["files"]:
            lines = item["source"].splitlines(keepends=True)
            for index, line in enumerate(lines):
                changed = line.replace(
                    "from pydantic import BaseSettings",
                    "from pydantic_settings import BaseSettings",
                ).replace(
                    "from collections import Mapping",
                    "from collections.abc import Mapping",
                )
                if changed != line:
                    edits.append(
                        {
                            "path": item["path"],
                            "start_line": index + 1,
                            "end_line": index + 1,
                            "old_sha256": hashlib.sha256(line.encode()).hexdigest(),
                            "new_text": changed,
                            "reason": "Migrate the removed application import.",
                        }
                    )
        self.assertNotIn("enum", json.dumps(request.schema))
        return ModelResponse(
            "Contract test double",
            request.model,
            request.model,
            "test",
            {},
            1,
            {
                "schema_version": 1,
                "source_sha": data["source_sha"],
                "diagnosis": "Migrate removed import.",
                "edits": edits,
            },
            {},
        )

    def test_two_no_enum_migrations_and_multi_file_verification(self):
        from v2_pipeline import run

        for task in ["v2-settings", "v2-collections", "v2-multifile"]:
            events = []
            with (
                self.subTest(task=task),
                patch("v2_pipeline.generate", side_effect=self.generate),
            ):
                run(
                    lambda name, data: events.append({"event": name, **data}),
                    task,
                    task,
                )
            result = events[-1]
            self.assertEqual(result["event"], "result")
            self.assertEqual(
                result["verification_scope"], "original suite plus independent checks"
            )
            self.assertTrue(result["independent_checks"]["passed"])
            self.assertEqual(
                result["baseline_tests"].keys(), result["verification_tests"].keys()
            )
            self.assertTrue(result["source_sha"])
            self.assertTrue(result["image_digest"])
            if task == "v2-multifile":
                self.assertEqual(len(result["changed_paths"]), 2)

    def test_independent_guard_catches_patch_that_only_satisfies_original_test(self):
        from v2_pipeline import run, RepairFailure
        from providers.base import ModelResponse

        def weak(request):
            data = json.loads(request.messages[-1]["content"])
            item = data["context"]["files"][0]
            text = item["source"]
            lines = text.splitlines(keepends=True)
            edit = {
                "path": item["path"],
                "start_line": 1,
                "end_line": len(lines),
                "old_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "new_text": text.replace(
                    "from pydantic import BaseSettings",
                    "from pydantic_settings import BaseSettings",
                ).replace(
                    "return {'service_name': settings.service_name, 'port': settings.port}",
                    "return {'service_name': 'bridge'}",
                ),
                "reason": "Unsafe semantic shortcut.",
            }
            return ModelResponse(
                "Test double",
                request.model,
                request.model,
                "weak",
                {},
                1,
                {
                    "schema_version": 1,
                    "source_sha": data["source_sha"],
                    "diagnosis": "Shortcut existing case.",
                    "edits": [edit],
                },
                {},
            )

        events = []
        with (
            patch("v2_pipeline.generate", side_effect=weak),
            self.assertRaises(RepairFailure),
        ):
            run(
                lambda n, d: events.append({"event": n, **d}),
                "negative",
                "v2-settings",
                attempts=1,
            )
        self.assertFalse(any(e["event"] == "result" for e in events))
        self.assertTrue(
            any(
                e["event"] == "rejected"
                and e["rejection_reason"] == "Independent behavior checks failed."
                for e in events
            )
        )

    def test_supervisor_rejects_candidate_printed_verdict(self):
        from server import sandbox

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.chmod(0o755)
            (root / "app").mkdir()
            (root / "app/records.py").write_text(
                "from dataclasses import sys\nprint('{\"passed\":true}')\nsys.exit(0)\n"
            )
            code, output = sandbox(
                [
                    "python",
                    "-I",
                    "/opt/versionbridge/independent_tests.py",
                    "v2-collections",
                ],
                lambda *a: None,
                root,
            )
            self.assertNotEqual(code, 0, output)
            self.assertIn("Independent behavioral comparison failed", output)

    def test_baseline_pass_is_inconclusive_and_never_calls_model(self):
        from v2_pipeline import run, RepairFailure

        with (
            patch(
                "v2_pipeline.execute",
                return_value=(0, "already passes", {"test_x": "passed"}),
            ),
            patch("v2_pipeline.generate") as model,
        ):
            with self.assertRaises(RepairFailure) as raised:
                run(lambda *a: None, "passing", "v2-settings")
        self.assertEqual(raised.exception.outcome, "inconclusive")
        model.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
