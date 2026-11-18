"""P28-06: isolated authorization tests. No AWS or live retrieval."""
import unittest
from unittest.mock import Mock

from phase28.authorization import (
    AccessDenied, DocumentScope, DomainAuthorizer, Principal, guarded_retrieve,
)


class TestAuthorization(unittest.TestCase):
    def setUp(self):
        self.policy = DomainAuthorizer({
            "sales": frozenset({"orders", "contracts"}),
            "finance": frozenset({"invoices"}),
        })
        self.actor = Principal("user-1", "tenant-a", frozenset({"sales"}))

    def test_authorized_read_calls_retriever_with_scope(self):
        scope = DocumentScope("tenant-a", "orders")
        retriever = Mock(return_value=["order-1"])
        self.assertEqual(guarded_retrieve(principal=self.actor, scope=scope,
                         authorizer=self.policy, retrieve=retriever), ["order-1"])
        retriever.assert_called_once_with(scope)

    def test_unauthorized_domain_does_not_retrieve(self):
        retriever = Mock()
        with self.assertRaises(AccessDenied):
            guarded_retrieve(principal=self.actor,
                             scope=DocumentScope("tenant-a", "invoices"),
                             authorizer=self.policy, retrieve=retriever)
        retriever.assert_not_called()

    def test_cross_tenant_does_not_retrieve(self):
        retriever = Mock()
        with self.assertRaises(AccessDenied):
            guarded_retrieve(principal=self.actor,
                             scope=DocumentScope("tenant-b", "orders"),
                             authorizer=self.policy, retrieve=retriever)
        retriever.assert_not_called()

    def test_unknown_role_denied(self):
        actor = Principal("user-2", "tenant-a", frozenset({"admin"}))
        with self.assertRaises(AccessDenied):
            self.policy.authorize(actor, DocumentScope("tenant-a", "orders"))

    def test_untrusted_subject_rejected(self):
        with self.assertRaises(ValueError):
            Principal("user\nsecret", "tenant-a", frozenset({"sales"}))

    def test_policy_rejects_mutable_grants(self):
        with self.assertRaises(ValueError):
            DomainAuthorizer({"sales": {"orders"}})


if __name__ == "__main__":
    unittest.main()
