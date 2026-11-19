"""P28-09: offline tests, temporary SQLite, no boto3 or AWS network."""
from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from phase28.bedrock_client import (
    BedrockInferenceClient, InferenceDisabledError, InferenceResponseError,
    InferenceResult,
)
from phase28.budget import BudgetExceededError, ModelPricing
from phase28.config import AISettings
from phase28.persistent_adapter import PersistentBudgetedBedrockAdapter
from phase28.persistent_budget import PersistentInferenceBudget


def converse_response(in_tokens=5, out_tokens=4):
    return {
        "output": {"message": {"content": [{"text": "Order ready"}]}},
        "usage": {"inputTokens": in_tokens, "outputTokens": out_tokens},
        "stopReason": "end_turn",
    }


class TestPersistentBudgetedAdapter(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "quotas.db"
        self.settings = AISettings(
            live_inference=True, live_inference_ack=True,
            max_input_tokens=100, max_output_tokens=20,
            max_requests_per_minute=2, max_daily_requests=3,
        )
        self.pricing = ModelPricing(Decimal("1"), Decimal("2"))
        self.runtime = Mock()
        self.runtime.converse.return_value = converse_response()
        self.ledger = self.new_ledger()
        self.adapter = self.make_adapter()

    def new_ledger(self):
        return PersistentInferenceBudget(self.path, self.settings,
                                         self.pricing, Decimal("0.01"))

    def make_adapter(self, bound=10, settings=None, client=None, ledger=None):
        cfg = settings or self.settings
        return PersistentBudgetedBedrockAdapter(
            cfg, client or BedrockInferenceClient(cfg, self.runtime),
            ledger or self.ledger,
            estimate_input_tokens=lambda _: bound,
        )

    def test_success_reconciles_durable_charge(self):
        result = self.adapter.infer("Order status?")
        self.assertEqual(result.text, "Order ready")
        self.runtime.converse.assert_called_once()
        snapshot = self.new_ledger().snapshot()
        self.assertEqual(snapshot.daily_requests, 1)
        self.assertEqual(snapshot.pending, 0)
        self.assertEqual(snapshot.charged_and_reserved_usd, Decimal("0.000013"))

    def test_timeout_retains_full_charge_after_restart(self):
        self.runtime.converse.side_effect = TimeoutError("unknown provider outcome")
        with self.assertRaises(TimeoutError):
            self.adapter.infer("Order status?")
        snapshot = self.new_ledger().snapshot()
        self.assertEqual(snapshot.pending, 0)
        self.assertEqual(snapshot.charged_and_reserved_usd, Decimal("0.000050"))

    def test_throttle_retains_full_charge_without_retry(self):
        self.runtime.converse.side_effect = RuntimeError("mock throttle")
        with self.assertRaises(RuntimeError):
            self.adapter.infer("Order status?")
        self.assertEqual(self.runtime.converse.call_count, 1)
        self.assertEqual(self.new_ledger().snapshot().charged_and_reserved_usd, Decimal("0.000050"))

    def test_malformed_converse_retains_full_charge(self):
        self.runtime.converse.return_value = {}
        with self.assertRaises(InferenceResponseError):
            self.adapter.infer("Order status?")
        self.assertEqual(self.new_ledger().snapshot().charged_and_reserved_usd, Decimal("0.000050"))

    def test_usage_above_reservation_requires_manual_reconciliation(self):
        self.runtime.converse.return_value = converse_response(in_tokens=11)
        with self.assertRaises(BudgetExceededError):
            self.adapter.infer("Order status?")
        self.assertEqual(self.new_ledger().snapshot().pending, 1)
        self.assertEqual(self.new_ledger().snapshot().charged_and_reserved_usd, Decimal("0.000050"))

    def test_preflight_limit_blocks_runtime(self):
        with self.assertRaises(BudgetExceededError):
            self.make_adapter(bound=101).infer("Order status?")
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.new_ledger().snapshot().daily_requests, 0)

    def test_minute_limit_shared_across_ledger_instances(self):
        self.adapter.infer("One")
        self.make_adapter(ledger=self.new_ledger()).infer("Two")
        with self.assertRaises(BudgetExceededError):
            self.adapter.infer("Three")
        self.assertEqual(self.runtime.converse.call_count, 2)

    def test_disabled_settings_never_create_reservation(self):
        disabled = AISettings(live_inference=False, live_inference_ack=False)
        ledger = PersistentInferenceBudget(self.path, disabled, self.pricing, Decimal("0.01"))
        adapter = self.make_adapter(settings=disabled, ledger=ledger)
        with self.assertRaises(InferenceDisabledError):
            adapter.infer("Order status?")
        self.runtime.converse.assert_not_called()
        self.assertEqual(ledger.snapshot().daily_requests, 0)

    def test_invalid_prompt_and_token_bound_never_reserve(self):
        with self.assertRaises(ValueError):
            self.adapter.infer("   ")
        with self.assertRaises(ValueError):
            self.make_adapter(bound=True).infer("Order status?")
        self.assertEqual(self.new_ledger().snapshot().daily_requests, 0)

    def test_mismatched_model_id_retains_charge(self):
        altered = Mock(spec=BedrockInferenceClient)
        altered.settings = self.settings
        altered.infer.return_value = InferenceResult(
            "Answer", "other-model", 4, 3, "end_turn")
        # Contract allows only actual BedrockInferenceClient; install a test
        # double on the real client after constructing the adapter.
        client = BedrockInferenceClient(self.settings, self.runtime)
        client.infer = altered.infer
        adapter = self.make_adapter(client=client)
        with self.assertRaises(ValueError):
            adapter.infer("Order status?")
        self.assertEqual(self.new_ledger().snapshot().pending, 0)
        self.assertEqual(self.new_ledger().snapshot().charged_and_reserved_usd, Decimal("0.000050"))

    def test_reject_mismatched_settings(self):
        other = AISettings(live_inference=True, live_inference_ack=True)
        ledger = PersistentInferenceBudget(self.path, other, self.pricing, Decimal("0.01"))
        with self.assertRaises(ValueError):
            self.make_adapter(ledger=ledger)


if __name__ == "__main__":
    unittest.main()
