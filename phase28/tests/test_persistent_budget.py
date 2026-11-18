"""P28-05: No AWS access; uses a temporary local SQLite file."""
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from phase28.budget import BudgetExceededError, ModelPricing
from phase28.config import AISettings
from phase28.persistent_budget import PersistentInferenceBudget


class TestPersistentInferenceBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.sqlite3'
        self.settings = AISettings(max_requests_per_minute=2, max_daily_requests=3)
        self.pricing = ModelPricing(Decimal('1'), Decimal('2'))

    def store(self, cap='0.01'):
        return PersistentInferenceBudget(self.path, self.settings,
                                         self.pricing, Decimal(cap))

    def test_defaults_create_no_inference_or_credentials(self):
        store = self.store()
        self.assertEqual(store.snapshot().daily_requests, 0)
        self.assertEqual(store.snapshot().pending, 0)

    def test_restart_keeps_reservation(self):
        one = self.store()
        reservation = one.reserve(10, 20)
        two = self.store()
        self.assertEqual(two.snapshot().pending, 1)
        self.assertEqual(two.snapshot().charged_and_reserved_usd, Decimal('0.00005'))
        two.settle(reservation, success=True, input_tokens=5, output_tokens=4)
        self.assertEqual(self.store().snapshot().charged_and_reserved_usd, Decimal('0.000013'))

    def test_minute_cap_shared_by_two_instances(self):
        a, b = self.store(), self.store()
        a.reserve(10, 20)
        b.reserve(10, 20)
        with self.assertRaises(BudgetExceededError):
            a.reserve(10, 20)

    def test_daily_usd_cap(self):
        store = self.store(cap='0.00005')
        store.reserve(10, 20)
        with self.assertRaises(BudgetExceededError):
            store.reserve(10, 20)

    def test_unknown_outcome_retains_full_cost(self):
        store = self.store()
        r = store.reserve(10, 20)
        self.assertEqual(store.settle(r, success=False), Decimal('0.00005'))
        self.assertEqual(self.store().snapshot().pending, 0)
        self.assertEqual(self.store().snapshot().charged_and_reserved_usd, Decimal('0.00005'))

    def test_excess_usage_does_not_refund(self):
        store = self.store()
        r = store.reserve(10, 20)
        with self.assertRaises(BudgetExceededError):
            store.settle(r, success=True, input_tokens=11, output_tokens=1)
        self.assertEqual(self.store().snapshot().pending, 1)

    def test_duplicate_settlement_rejected(self):
        store = self.store()
        r = store.reserve(10, 20)
        store.settle(r, success=False)
        with self.assertRaises(ValueError):
            store.settle(r, success=False)

    def test_bad_token_type_rejected(self):
        store = self.store()
        with self.assertRaises(BudgetExceededError):
            store.reserve(True, 20)
        self.assertEqual(store.snapshot().daily_requests, 0)

    def test_invalid_input_caps_rejected(self):
        with self.assertRaises(ValueError):
            PersistentInferenceBudget(self.path, self.settings, self.pricing, Decimal('-1'))


if __name__ == '__main__':
    unittest.main()
