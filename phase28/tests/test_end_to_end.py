"""P28-08: offline, in-process governed service + quota + Converse integration."""
import unittest
from decimal import Decimal
from unittest.mock import Mock

from phase28.authorization import AccessDenied, DomainAuthorizer, Principal
from phase28.bedrock_client import BedrockInferenceClient
from phase28.budget import InMemoryInferenceBudget, ModelPricing
from phase28.budgeted_adapter import BudgetedBedrockAdapter
from phase28.config import AISettings
from phase28.service import ServiceError, answer_business_question


def response(*, text="Order is ready", input_tokens=6, output_tokens=4):
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens},
        "stopReason": "end_turn",
    }


class TestEndToEnd(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # These flags authorize only an injected test double. No boto3 or AWS.
        self.settings = AISettings(
            live_inference=True, live_inference_ack=True,
            max_input_tokens=100, max_output_tokens=20,
            max_requests_per_minute=2, max_daily_requests=3,
        )
        self.principal = Principal("alice", "tenant-a", frozenset({"sales"}))
        self.authorizer = DomainAuthorizer({"sales": frozenset({"orders"})})
        self.runtime = Mock()
        self.runtime.converse.return_value = response()
        self.budget = InMemoryInferenceBudget(
            self.settings,
            ModelPricing(Decimal("1.00"), Decimal("2.00")),
            max_daily_usd=Decimal("0.01"),
        )
        self.adapter = BudgetedBedrockAdapter(
            self.settings,
            BedrockInferenceClient(self.settings, runtime_client=self.runtime),
            self.budget,
            estimate_input_tokens=lambda _: 10,  # TEST FIXTURE, not safe for live calls
        )
        self.retriever = Mock(return_value={"sources": [
            {"id": "src1", "tenant_id": "tenant-a", "domain": "orders", "record_id": "order1"}
        ]})
        self.audit = Mock()
        self.mutations = Mock()
        self.model = Mock(side_effect=self._generate)

    def _generate(self, question, evidence):
        # Pass only after service authorization and retrieval checks.
        model_result = self.adapter.infer(question)
        return {"answer": model_result.text, "cited_source_ids": [evidence["sources"][0]["id"]]}

    async def invoke(self, **changes):
        inputs = {
            "actor": "alice", "domain": "orders", "question": "Order status?",
            "principal": self.principal, "authorizer": self.authorizer,
            "retrieve": self.retriever, "generate": self.model, "audit_sink": self.audit,
            "use_model": True,
        }
        inputs.update(changes)
        return await answer_business_question(**inputs)

    async def test_authorized_flow_reconciles_cost_and_stays_read_only(self):
        result = await self.invoke()
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["cited_source_ids"], ["src1"])
        self.assertEqual(result["actions_taken"], [])
        self.retriever.assert_called_once()
        self.runtime.converse.assert_called_once()
        self.mutations.assert_not_called()
        snap = self.budget.snapshot()
        self.assertEqual(snap.daily_requests, 1)
        self.assertEqual(snap.pending_reservations, 0)
        self.assertEqual(snap.committed_and_reserved_usd, Decimal("0.000014"))
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "success")

    async def test_unauthorized_request_never_retrieves_or_infers(self):
        with self.assertRaises(AccessDenied):
            await self.invoke(domain="finance")
        self.retriever.assert_not_called()
        self.model.assert_not_called()
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.budget.snapshot().daily_requests, 0)
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "deny")

    async def test_cross_tenant_evidence_never_infers(self):
        self.retriever.return_value = {"sources": [
            {"id": "src2", "tenant_id": "tenant-b", "domain": "orders"}
        ]}
        with self.assertRaises(ServiceError):
            await self.invoke()
        self.model.assert_not_called()
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.budget.snapshot().daily_requests, 0)

    async def test_retrieval_only_does_not_infer_or_reserve(self):
        result = await self.invoke(use_model=False)
        self.assertEqual(result["status"], "retrieval_only")
        self.model.assert_not_called()
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.budget.snapshot().daily_requests, 0)

    async def test_timeout_retains_full_reservation(self):
        self.runtime.converse.side_effect = TimeoutError("simulated")
        with self.assertRaises(ServiceError):
            await self.invoke()
        snap = self.budget.snapshot()
        self.assertEqual(snap.daily_requests, 1)
        self.assertEqual(snap.pending_reservations, 0)
        self.assertEqual(snap.committed_and_reserved_usd, Decimal("0.000050"))
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "error")

    async def test_throttle_retains_full_reservation(self):
        self.runtime.converse.side_effect = RuntimeError("simulated throttle")
        with self.assertRaises(ServiceError):
            await self.invoke()
        self.assertEqual(self.budget.snapshot().committed_and_reserved_usd, Decimal("0.000050"))

    async def test_malformed_reply_retains_full_reservation(self):
        self.runtime.converse.return_value = {}
        with self.assertRaises(ServiceError):
            await self.invoke()
        self.assertEqual(self.budget.snapshot().committed_and_reserved_usd, Decimal("0.000050"))

    async def test_unknown_citation_rejected_without_business_write(self):
        self.model = Mock(return_value={"answer": "Made up", "cited_source_ids": ["src999"]})
        with self.assertRaises(ServiceError):
            await self.invoke()
        self.mutations.assert_not_called()
        self.runtime.converse.assert_not_called()
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "error")


if __name__ == "__main__":
    unittest.main()
