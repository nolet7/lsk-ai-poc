"""P28-06: audit record allowlist tests."""
import unittest
from phase28.audit import audit_event


class TestAudit(unittest.TestCase):
    def test_sanitized_event(self):
        event = audit_event(request_id="req-1", actor="user-1",
                            tenant_id="tenant-a", domain="orders",
                            outcome="deny", source_ids=[])
        self.assertEqual(event["outcome"], "deny")
        self.assertEqual(event["tenant_id"], "tenant-a")
        self.assertEqual(set(event), {"timestamp", "request_id", "actor",
                                     "tenant_id", "domain", "outcome",
                                     "source_ids", "model_id"})

    def test_invalid_outcome_rejected(self):
        with self.assertRaises(ValueError):
            audit_event(request_id="req-1", actor="user-1", domain="orders",
                        outcome="password=secret", source_ids=[])

    def test_newline_source_rejected(self):
        with self.assertRaises(ValueError):
            audit_event(request_id="req-1", actor="user-1", domain="orders",
                        outcome="deny", source_ids=["doc-1\nsecret"])


if __name__ == "__main__":
    unittest.main()
