"""Offline acceptance tests for P28-03. No AWS/network access."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from phase28.budget import BudgetExceededError, InMemoryInferenceBudget, ModelPricing
from phase28.config import AISettings


class FakeTime:
    def __init__(self):
        self.seconds = 1000.0
        self.date = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)

    def advance(self, seconds):
        self.seconds += seconds
        self.date += timedelta(seconds=seconds)


class TestInferenceBudget(unittest.TestCase):
    def setUp(self):
        self.fake = FakeTime()
        self.config = AISettings(max_requests_per_minute=2, max_daily_requests=3)
        self.pricing = ModelPricing(Decimal("1.00"), Decimal("2.00"))

    def make_guard(self, cap="1"):
        return InMemoryInferenceBudget(
            self.config, self.pricing, Decimal(cap),
            clock=lambda: self.fake.seconds,
            utcnow=lambda: self.fake.date,
        )

    def test_rates_must_be_explicit_nonnegative_decimals(self):
        with self.assertRaises(ValueError):
            ModelPricing(Decimal("NaN"), Decimal("2"))
        with self.assertRaises(ValueError):
            ModelPricing(Decimal("-1"), Decimal("2"))

    def test_reserve_uses_worst_case_preflight_budget(self):
        guard = self.make_guard("0.0003")
        with self.assertRaises(BudgetExceededError):
            guard.reserve(200, 100)
        self.assertEqual(guard.snapshot().daily_requests, 0)

    def test_per_request_token_limits(self):
        guard = self.make_guard()
        with self.assertRaises(BudgetExceededError):
            guard.reserve(self.config.max_input_tokens + 1, 5)
        with self.assertRaises(ValueError):
            guard.reserve(True, 5)

    def test_minute_limit_and_expiry(self):
        guard = self.make_guard()
        guard.reserve(10, 10)
        guard.reserve(10, 10)
        with self.assertRaises(BudgetExceededError):
            guard.reserve(10, 10)
        self.fake.advance(60)
        guard.reserve(10, 10)
        self.assertEqual(guard.snapshot().daily_requests, 3)

    def test_daily_request_limit(self):
        guard = self.make_guard()
        guard.reserve(10, 10)
        guard.reserve(10, 10)
        self.fake.advance(60)
        guard.reserve(10, 10)
        with self.assertRaises(BudgetExceededError):
            guard.reserve(10, 10)

    def test_actual_usage_reconciles_reserved_cost(self):
        guard = self.make_guard()
        r = guard.reserve(100, 100)
        charged = guard.settle(r, success=True, input_tokens=20, output_tokens=10)
        self.assertEqual(charged, Decimal("0.00004"))
        self.assertEqual(guard.snapshot().committed_and_reserved_usd, charged)
        self.assertEqual(guard.snapshot().pending_reservations, 0)

    def test_timeout_conservatively_keeps_full_charge(self):
        guard = self.make_guard()
        r = guard.reserve(100, 100)
        guard.settle(r, success=False)
        self.assertEqual(guard.snapshot().committed_and_reserved_usd, Decimal("0.0003"))
        with self.assertRaises(ValueError):
            guard.settle(r, success=False)

    def test_bad_usage_does_not_release_reservation(self):
        guard = self.make_guard()
        r = guard.reserve(100, 100)
        with self.assertRaises(BudgetExceededError):
            guard.settle(r, success=True, input_tokens=101, output_tokens=1)
        self.assertEqual(guard.snapshot().pending_reservations, 1)

    def test_day_rollover_requires_zero_pending(self):
        guard = self.make_guard()
        r = guard.reserve(10, 10)
        self.fake.advance(86400)
        with self.assertRaises(BudgetExceededError):
            guard.reserve(10, 10)
        guard.settle(r, success=False)
        guard.reserve(10, 10)
        self.assertEqual(guard.snapshot().daily_requests, 1)


if __name__ == "__main__":
    unittest.main()
