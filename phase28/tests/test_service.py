"""Phase 28 gateway seams: enforce deny-before-retrieve; gateway P28-07 pending."""
import unittest
from unittest.mock import Mock
from phase28.authorization import (
    AccessDenied, DocumentScope, DomainAuthorizer, Principal, guarded_retrieve,
)


class ServiceTasks(unittest.TestCase):
    def test_unauthorized_domain_does_not_retrieve(self):
        actor = Principal("user-1", "tenant-a", frozenset({"sales"}))
        authorizer = DomainAuthorizer({"sales": frozenset({"orders"})})
        retrieval = Mock()
        with self.assertRaises(AccessDenied):
            guarded_retrieve(
                principal=actor,
                scope=DocumentScope("tenant-a", "invoices"),
                authorizer=authorizer,
                retrieve=retrieval,
            )
        retrieval.assert_not_called()

    @unittest.skip("TASK P28-07: preserve existing gateway API contracts")
    def test_retrieval_only_does_not_call_model(self):
        pass
