"""P28-11: offline startup, IAM identity fixture and governed service tests."""
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from phase28.authorization import AccessDenied, DomainAuthorizer, Principal
from phase28.aws_security import RuntimeApproval
from phase28.budget import ModelPricing
from phase28.config import AISettings
from phase28.deployment import (
    DeploymentIdentity, DeploymentRejected, build_governed_deployment,
    verify_workload_identity,
)
from phase28.persistent_budget import PersistentInferenceBudget
from phase28.service import ServiceError


def response(text='{"answer":"Ready","cited_source_ids":["src1"]}'):
    return {"output": {"message": {"content": [{"text": text}]}},
            "usage": {"inputTokens": 5, "outputTokens": 4},
            "stopReason": "end_turn"}


class TestDeployment(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.settings = AISettings(live_inference=True, live_inference_ack=True,
                                   max_input_tokens=100, max_output_tokens=20)
        self.ledger = PersistentInferenceBudget(
            Path(t.name) / "quota.db", self.settings,
            ModelPricing(Decimal("1"), Decimal("2")), Decimal("0.01"))
        self.identity = DeploymentIdentity(
            "123456789012", "arn:aws:iam::123456789012:role/lsk-bedrock-runtime",
            "vpce-0123456789abcdef0")
        self.probe = Mock(return_value={"Account": "123456789012",
                    "Arn": "arn:aws:sts::123456789012:assumed-role/lsk-bedrock-runtime/session1"})
        self.runtime = Mock()
        self.runtime.converse.return_value = response()
        self.client_factory = Mock(return_value=self.runtime)
        self.config_factory = Mock(return_value=object())
        self.retriever = Mock(return_value={"sources": [{
            "id": "src1", "tenant_id": "tenant-a", "domain": "orders",
            "record_id": "o1", "content": "Order is ready"}]})
        self.audit = Mock()
        self.principal = Principal("alice", "tenant-a", frozenset({"sales"}))
        self.policy = DomainAuthorizer({"sales": frozenset({"orders"})})

    def build(self, **changes):
        args = dict(settings=self.settings, approval=RuntimeApproval(
            True, self.settings.aws_region, self.settings.model_id),
            identity=self.identity, identity_probe=self.probe,
            client_factory=self.client_factory, config_factory=self.config_factory,
            ledger=self.ledger, estimate_input_tokens=lambda _: 10,
            authorizer=self.policy, retrieve=self.retriever, audit_sink=self.audit)
        args.update(changes)
        return build_governed_deployment(**args)

    def test_matching_sts_assumed_role(self):
        verify_workload_identity(expected=self.identity, probe=self.probe)
        self.probe.assert_called_once()

    def test_wrong_account_prevents_sdk(self):
        self.probe.return_value = {"Account": "000000000000",
          "Arn": "arn:aws:sts::000000000000:assumed-role/lsk-bedrock-runtime/session1"}
        with self.assertRaises(DeploymentRejected): self.build()
        self.client_factory.assert_not_called()

    def test_wrong_role_prevents_sdk(self):
        self.probe.return_value = {"Account": "123456789012",
          "Arn": "arn:aws:sts::123456789012:assumed-role/admin/session1"}
        with self.assertRaises(DeploymentRejected): self.build()
        self.client_factory.assert_not_called()

    def test_missing_probe_prevents_sdk(self):
        with self.assertRaises(DeploymentRejected): self.build(identity_probe=None)
        self.client_factory.assert_not_called()

    def test_default_disabled_prevents_probe_and_sdk(self):
        with self.assertRaises(DeploymentRejected): self.build(settings=AISettings())
        self.probe.assert_not_called()
        self.client_factory.assert_not_called()

    def test_inmemory_budget_rejected(self):
        with self.assertRaises(DeploymentRejected): self.build(ledger=object())
        self.client_factory.assert_not_called()

    def test_missing_audit_sink_rejected(self):
        with self.assertRaises(DeploymentRejected): self.build(audit_sink=None)
        self.client_factory.assert_not_called()

    def test_invalid_vpce_rejected(self):
        with self.assertRaises(ValueError):
            DeploymentIdentity("123456789012", self.identity.role_arn, "*")

    async def test_retrieval_only_never_calls_bedrock_or_ledger(self):
        deployment = self.build()
        result = await deployment.answer(principal=self.principal, domain="orders",
                                         question="Status?", use_model=False)
        self.assertEqual(result["status"], "retrieval_only")
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.ledger.snapshot().daily_requests, 0)

    async def test_denied_domain_prevents_retrieval_and_bedrock(self):
        deployment = self.build()
        with self.assertRaises(AccessDenied):
            await deployment.answer(principal=self.principal, domain="invoices",
                                    question="Status?", use_model=True)
        self.retriever.assert_not_called()
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.ledger.snapshot().daily_requests, 0)

    async def test_successful_structured_reply_charges_sqlite(self):
        deployment = self.build()
        result = await deployment.answer(principal=self.principal, domain="orders",
                                         question="Status?", use_model=True)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["cited_source_ids"], ["src1"])
        self.assertEqual(result["actions_taken"], [])
        self.assertEqual(self.ledger.snapshot().daily_requests, 1)
        self.assertEqual(self.ledger.snapshot().charged_and_reserved_usd, Decimal("0.000013"))
        self.runtime.converse.assert_called_once()

    async def test_unapproved_citation_fails_closed(self):
        self.runtime.converse.return_value = response(
            '{"answer":"Unknown","cited_source_ids":["other"]}')
        with self.assertRaises(ServiceError):
            await self.build().answer(principal=self.principal, domain="orders",
                                      question="Status?", use_model=True)
        self.assertEqual(self.ledger.snapshot().daily_requests, 1)
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "error")

    async def test_bad_model_json_fails_closed_without_refund(self):
        self.runtime.converse.return_value = response("not-json")
        with self.assertRaises(ServiceError):
            await self.build().answer(principal=self.principal, domain="orders",
                                      question="Status?", use_model=True)
        self.assertEqual(self.ledger.snapshot().charged_and_reserved_usd, Decimal("0.000013"))

    async def test_timeout_keeps_full_charge(self):
        self.runtime.converse.side_effect = TimeoutError("network")
        with self.assertRaises(ServiceError):
            await self.build().answer(principal=self.principal, domain="orders",
                                      question="Status?", use_model=True)
        self.assertEqual(self.ledger.snapshot().charged_and_reserved_usd, Decimal("0.000050"))


if __name__ == "__main__":
    unittest.main()
