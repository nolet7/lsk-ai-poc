
"""P28-04: Offline tests for budget-controlled Bedrock calls."""

import unittest
from decimal import Decimal
from unittest.mock import Mock

from phase28.config import AISettings
from phase28.bedrock_client import (
    BedrockInferenceClient,
    InferenceDisabledError,
    InferenceResponseError,
)
from phase28.budget import (
    BudgetExceededError,
    InMemoryInferenceBudget,
    ModelPricing,
)
from phase28.budgeted_adapter import BudgetedBedrockAdapter


def settings(enabled=True, **overrides):
    values = dict(
        live_inference=enabled,
        live_inference_ack=enabled,
        max_input_tokens=100,
        max_output_tokens=20,
        max_requests_per_minute=2,
        max_daily_requests=3,
    )
    values.update(overrides)
    return AISettings(**values)


def response(input_tokens=5, output_tokens=4):
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "Hello from Bedrock"}],
            }
        },
        "usage": {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        },
        "stopReason": "end_turn",
    }


def make_adapter(cfg=None, estimated_tokens=10):
    cfg = cfg or settings()
    fake = Mock()
    fake.converse.return_value = response()

    client = BedrockInferenceClient(
        cfg,
        runtime_client=fake,
    )

    pricing = ModelPricing(
        input_per_million_usd=Decimal("1.00"),
        output_per_million_usd=Decimal("2.00"),
    )

    budget = InMemoryInferenceBudget(
        cfg,
        pricing,
        max_daily_usd=Decimal("0.01"),
    )

    adapter = BudgetedBedrockAdapter(
        cfg,
        client,
        budget,
        estimate_input_tokens=lambda _: estimated_tokens,
    )

    return adapter, budget, fake


class TestBudgetedBedrockAdapter(unittest.TestCase):

    def test_successful_inference(self):
        adapter, budget, fake = make_adapter()

        result = adapter.infer("Hello")

        self.assertEqual(result.text, "Hello from Bedrock")
        self.assertEqual(result.input_tokens, 5)
        self.assertEqual(result.output_tokens, 4)
        fake.converse.assert_called_once()

    def test_success_reconciles_cost(self):
        adapter, budget, _ = make_adapter()

        adapter.infer("Hello")

        snapshot = budget.snapshot()

        self.assertEqual(snapshot.daily_requests, 1)
        self.assertEqual(snapshot.pending_reservations, 0)
        self.assertEqual(
            snapshot.committed_and_reserved_usd,
            Decimal("0.000013"),
        )

    def test_disabled_inference_fails_closed(self):
        adapter, budget, fake = make_adapter(
            settings(enabled=False)
        )

        with self.assertRaises(InferenceDisabledError):
            adapter.infer("Hello")

        fake.converse.assert_not_called()
        self.assertEqual(budget.snapshot().daily_requests, 0)

    def test_empty_prompt_does_not_reserve(self):
        adapter, budget, fake = make_adapter()

        with self.assertRaises(ValueError):
            adapter.infer("   ")

        fake.converse.assert_not_called()
        self.assertEqual(budget.snapshot().daily_requests, 0)

    def test_bad_token_estimate_rejected(self):
        adapter, budget, fake = make_adapter(
            estimated_tokens=0
        )

        with self.assertRaises(ValueError):
            adapter.infer("Hello")

        fake.converse.assert_not_called()
        self.assertEqual(budget.snapshot().daily_requests, 0)

    def test_request_token_limit_enforced(self):
        adapter, budget, fake = make_adapter(
            estimated_tokens=101
        )

        with self.assertRaises(BudgetExceededError):
            adapter.infer("Hello")

        fake.converse.assert_not_called()
        self.assertEqual(budget.snapshot().daily_requests, 0)

    def test_minute_quota_enforced(self):
        adapter, budget, fake = make_adapter()

        adapter.infer("First")
        adapter.infer("Second")

        with self.assertRaises(BudgetExceededError):
            adapter.infer("Third")

        self.assertEqual(fake.converse.call_count, 2)
        self.assertEqual(budget.snapshot().daily_requests, 2)

    def test_timeout_retains_charge(self):
        adapter, budget, fake = make_adapter()
        fake.converse.side_effect = TimeoutError(
            "Simulated timeout"
        )

        with self.assertRaises(TimeoutError):
            adapter.infer("Hello")

        snapshot = budget.snapshot()

        self.assertEqual(snapshot.pending_reservations, 0)
        self.assertEqual(
            snapshot.committed_and_reserved_usd,
            Decimal("0.000050"),
        )

    def test_malformed_response_retains_charge(self):
        adapter, budget, fake = make_adapter()
        fake.converse.return_value = {}

        with self.assertRaises(InferenceResponseError):
            adapter.infer("Hello")

        self.assertEqual(
            budget.snapshot().committed_and_reserved_usd,
            Decimal("0.000050"),
        )

    def test_excess_actual_usage_fails_closed(self):
        adapter, budget, fake = make_adapter()
        fake.converse.return_value = response(
            input_tokens=11,
            output_tokens=4,
        )

        with self.assertRaises(BudgetExceededError):
            adapter.infer("Hello")

        self.assertEqual(
            budget.snapshot().pending_reservations,
            1,
        )


if __name__ == "__main__":
    unittest.main()
