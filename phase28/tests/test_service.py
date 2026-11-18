import unittest
from unittest.mock import Mock

from phase28.authorization import AccessDenied, DomainAuthorizer, Principal
from phase28.service import ServiceError, answer_business_question


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.principal = Principal("alice", "tenant-a", frozenset({"sales"}))
        self.policy = DomainAuthorizer({"sales": frozenset({"orders"})})
        self.retriever = Mock(return_value={"sources": [
            {"id": "src1", "tenant_id": "tenant-a", "domain": "orders", "record_id": "order1"}
        ]})
        self.generator = Mock(return_value={"answer": "Status is ready", "cited_source_ids": ["src1"]})
        self.audit = Mock()

    async def run_service(self, **kwargs):
        opts = dict(actor="alice", domain="orders", question="Status?",
                    principal=self.principal, authorizer=self.policy,
                    retrieve=self.retriever, generate=self.generator, audit_sink=self.audit)
        opts.update(kwargs)
        return await answer_business_question(**opts)

    async def test_retrieval_only_never_calls_model(self):
        result = await self.run_service()
        self.assertEqual(result["status"], "retrieval_only")
        self.assertEqual(result["actions_taken"], [])
        self.generator.assert_not_called()
        self.retriever.assert_called_once()

    async def test_unauthorized_domain_blocks_all_downstream(self):
        with self.assertRaises(AccessDenied):
            await self.run_service(domain="finance")
        self.retriever.assert_not_called()
        self.generator.assert_not_called()
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "deny")

    async def test_cross_tenant_response_fails_closed(self):
        self.retriever.return_value = {"sources": [
            {"id": "src1", "tenant_id": "tenant-b", "domain": "orders"}
        ]}
        with self.assertRaises(ServiceError):
            await self.run_service(use_model=True)
        self.generator.assert_not_called()

    async def test_model_cannot_cite_unretrieved_source(self):
        self.generator.return_value = {"answer": "Wrong", "cited_source_ids": ["src99"]}
        with self.assertRaises(ServiceError):
            await self.run_service(use_model=True)

    async def test_no_evidence_abstains(self):
        self.retriever.return_value = {"sources": []}
        result = await self.run_service(use_model=True)
        self.assertEqual(result["status"], "abstain")
        self.generator.assert_not_called()

    async def test_model_response_grounded_ids(self):
        result = await self.run_service(use_model=True)
        self.assertEqual(result["cited_source_ids"], ["src1"])
        self.assertEqual(result["actions_taken"], [])

    async def test_missing_verified_principal_rejected(self):
        with self.assertRaises(AccessDenied):
            await self.run_service(principal=None)
        self.retriever.assert_not_called()

    async def test_record_filter_prevents_model_use(self):
        result = await self.run_service(record_id="another", use_model=True)
        self.assertEqual(result["status"], "abstain")
        self.generator.assert_not_called()
