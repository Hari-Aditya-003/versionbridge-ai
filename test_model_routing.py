"""Unit tests for opt-in model routing; these require no Docker or paid API."""
import io
import json
import os
import unittest
from unittest.mock import patch

from inference import propose
from model_routing import plan_models
from profiles import PROFILES


class ModelRoutingTests(unittest.TestCase):
    def test_legacy_mode_unchanged(self):
        self.assertEqual(plan_models("sample", 2, None), ())
        self.assertEqual(plan_models("vultr", 2, ""), ())

    def test_attempts_use_distinct_models(self):
        pool = "glm-5.3-flash, deepseek-v4.1-flash-1017"
        self.assertEqual(plan_models("vultr", 1, pool), ("glm-5.3-flash",))
        self.assertEqual(plan_models("vultr", 2, pool),
                         ("glm-5.3-flash", "deepseek-v4.1-flash-1017"))

    def test_bad_configuration_is_rejected(self):
        pools = ["model1", "model1,model1", "model1,", ",model2", "model1,model2,model3",
                 "model1,model two", "model1,model2\\nhello"]
        for pool in pools:
            with self.subTest(pool=pool), self.assertRaises(ValueError):
                plan_models("vultr", 2, pool)
        with self.assertRaises(RuntimeError):
            plan_models("sample", 2, "one,two")

    def test_provider_override_used_and_attributed(self):
        response = {"id": "receipt", "model": "served-model",
                    "usage": {"total_tokens": 10},
                    "choices": [{"message": {"content": json.dumps({
                        "diagnosis": "Correct quantity multiplication.",
                        "replacement": "return unit_cents * quantity + fee_cents",
                    })}}]}
        with patch.dict(os.environ, {"VULTR_API_KEY": "fake", "VULTR_MODEL": "original"}, clear=True):
            with patch("inference.budget.reserve", return_value={"reservation_id": 1}):
                with patch("inference.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as send:
                    candidate = propose(PROFILES["billing"], "failure", "source", model_id="second")
        self.assertEqual(json.loads(send.call_args.args[0].data)["model"], "second")
        self.assertEqual(candidate.receipt["requested_model"], "second")
        self.assertEqual(candidate.receipt["served_model"], "served-model")

    def test_override_is_not_allowed_in_sample_mode(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            propose(PROFILES["billing"], "failure", "source", model_id="second")


if __name__ == "__main__":
    unittest.main()
