"""Offline security and workflow tests: no AWS, network, or business writes."""
from __future__ import annotations
import asyncio
import os
import unittest
from datetime import date,timedelta
from unittest.mock import Mock,patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from phase28.authorization import Principal,DomainAuthorizer
from phase28.fde_commercial.contracts import CommercialContext,ensure_case,ensure_evidence
from phase28.fde_commercial.graph import CommercialGraph
from phase28.fde_commercial.tools import InProcessTools
from phase28.fde_commercial.api import build_router

class FakeRepo:
    def __init__(self):
        self.calls=[]

    def case(self,ctx,po_id):
        self.calls.append(("case",ctx.tenant_id,po_id))
        return {"tenant_id":ctx.tenant_id,"po_id":po_id,"supplier_id":"supplier-9",
                "quantity":"2","contract_unit_price":"30.00",
                "invoice_total":"65.00","currency":"USD","invoice_id":"inv-1",
                "certificate_expiry":str(date.today()-timedelta(days=1))}

    def evidence(self,ctx,po_id):
        self.calls.append(("evidence",ctx.tenant_id,po_id))
        return [{"source_id":"contract-9","tenant_id":ctx.tenant_id,
                 "po_id":po_id,"content":"Synthetic supplier agreement approved for demo."}]

class WrongTenantRepo(FakeRepo):
    def case(self,ctx,po_id):
        row=super().case(ctx,po_id)
        row["tenant_id"]="different-tenant"
        return row

class WrongEvidenceRepo(FakeRepo):
    def evidence(self,ctx,po_id):
        rows=super().evidence(ctx,po_id)
        rows[0]["tenant_id"]="different-tenant"
        return rows

class FakeVerifier:
    def verify(self,token):
        from phase28.oidc import AuthenticationFailed
        if token=="buyer":
            return Principal("alice","tenant-a",frozenset({"procurement"}))
        if token=="reviewer":
            return Principal("bob","tenant-a",frozenset({"procurement_reviewer"}))
        raise AuthenticationFailed("Unauthorized")

class ContractTests(unittest.TestCase):
    def test_deterministic_variance_and_expiry(self):
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        case=FakeRepo().case(ctx,"PO-3")
        result=ensure_case(case,tenant_id="tenant-a",po_id="PO-3")
        self.assertEqual(result["variance"],"5.00")
        self.assertTrue(result["price_mismatch"])
        self.assertTrue(result["certificate_expired"])

    def test_malicious_cross_tenant_result_is_rejected(self):
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        case=FakeRepo().case(ctx,"PO-3")
        case["tenant_id"]="tenant-b"
        with self.assertRaises(ValueError):
            ensure_case(case,tenant_id=ctx.tenant_id,po_id="PO-3")

    def test_invalid_financial_data_rejected(self):
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        for value in ("NaN", "-1", "Infinity", "not-a-number"):
            case=FakeRepo().case(ctx,"PO-3")
            case["invoice_total"]=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                ensure_case(case,tenant_id=ctx.tenant_id,po_id="PO-3")

    def test_duplicate_and_foreign_evidence_rejected(self):
        rows=[{"source_id":"s1","tenant_id":"tenant-b","po_id":"PO-3","content":"secret"}]
        with self.assertRaises(ValueError):
            ensure_evidence(rows,tenant_id="tenant-a",po_id="PO-3")
        rows=[{"source_id":"s1","tenant_id":"tenant-a","po_id":"PO-3","content":"safe"}]*2
        with self.assertRaises(ValueError):
            ensure_evidence(rows,tenant_id="tenant-a",po_id="PO-3")

    def test_url_rejects_http_and_ssrf_config(self):
        from phase28.fde_commercial.mcp_client import validate_url
        for url in ("http://internal/mcp","https://user:pass@internal/mcp",
                    "https://internal/mcp?tenant=b", "https://internal/other"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                validate_url(url)

class GraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_four_step_read_only_flow(self):
        repo=FakeRepo()
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        result=await CommercialGraph(InProcessTools(repo)).run(ctx,"PO-3","Find mismatch")
        self.assertEqual(result["steps"],4)
        self.assertEqual(result["findings"]["variance"],"5.00")
        self.assertEqual(len(result["evidence"]),1)
        self.assertEqual(repo.calls,[("case","tenant-a","PO-3"),("evidence","tenant-a","PO-3")])

    async def test_cross_tenant_tool_result_denied(self):
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        with self.assertRaises(ValueError):
            await CommercialGraph(InProcessTools(WrongTenantRepo())).run(ctx,"PO-3","Find mismatch")

    async def test_cross_tenant_document_denied(self):
        ctx=CommercialContext("alice","tenant-a",frozenset({"procurement"}))
        with self.assertRaises(ValueError):
            await CommercialGraph(InProcessTools(WrongEvidenceRepo())).run(ctx,"PO-3","Find mismatch")

class APITests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepo()
        self.env=patch.dict(os.environ,{"LSK_BEDROCK_MODEL_ID":"test",
                                      "AWS_REGION":"us-east-2",
                                      "AI_LIVE_INFERENCE":"false",
                                      "AI_LIVE_INFERENCE_ACK":"false"})
        self.env.start()
        self.addCleanup(self.env.stop)
        app=FastAPI()
        grants=DomainAuthorizer({"procurement":frozenset({"procurement"}),
                                 "procurement_reviewer":frozenset({"procurement"})})
        def invalid_connection():
            raise AssertionError("No database access expected for safe retrieval tests")
        app.include_router(build_router(verifier=FakeVerifier(),authorizer=grants,
                                        connect=invalid_connection,
                                        tools=InProcessTools(self.repo)))
        self.client=TestClient(app)

    def request(self,token="buyer",**changes):
        return self.client.post("/v1/commercial/procurement/review",
                 headers={"Authorization":"Bearer "+token},
                 json={"po_id":"PO-3","question":"Find invoice difference",**changes})

    def test_read_only_verified_request(self):
        result=self.request()
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["findings"]["variance"],"5.00")
        self.assertIsNone(result.json()["proposal"])
        self.assertFalse(result.json()["erp_updated"])

    def test_deny_missing_invalid_token(self):
        result=self.client.post("/v1/commercial/procurement/review",
             json={"po_id":"PO-3","question":"Find invoice difference"})
        self.assertEqual(result.status_code,401)
        self.assertEqual(self.request(token="forged").status_code,401)
        self.assertEqual(self.repo.calls,[])

    def test_model_fail_closed(self):
        self.assertEqual(self.request(use_model=True).status_code,403)

    def test_proposal_requires_idempotency_key(self):
        self.assertEqual(self.request(propose_exception=True).status_code,422)

    def test_reviewer_must_have_role(self):
        res=self.client.post("/v1/commercial/procurement/exceptions/abc/decision",
          headers={"Authorization":"Bearer buyer"},json={"decision":"approved"})
        self.assertEqual(res.status_code,403)

if __name__=="__main__":
    unittest.main()
