"""Real PostgreSQL integration: synthetic tenant and review integrity."""
from __future__ import annotations
import os
import unittest
from uuid import uuid4
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None

from phase28.fde_commercial.contracts import CommercialContext, ensure_case

@unittest.skipUnless(os.getenv("LSK_TEST_PG_DSN") and psycopg is not None,
                     "PostgreSQL only in dedicated CI service")
class PostgreSQLCommercialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ["LSK_TEST_PG_DSN"]
        cls.connect=staticmethod(lambda: psycopg.connect(cls.dsn, connect_timeout=3))
        root=Path(__file__).resolve().parents[1]/"sql"
        with cls.connect() as db:
            db.execute((root/"001_init_postgres.sql").read_text())
            db.execute((root/"002_procurement.sql").read_text())
            db.execute((root/"003_procurement_knowledge.sql").read_text())

    def setUp(self):
        from phase28.fde_commercial.repository import ProcurementRepository
        self.repo=ProcurementRepository(self.connect)
        suffix=uuid4().hex[:12]
        self.tenant_a="tenant-"+suffix
        self.tenant_b="other-"+suffix
        self.po="PO-"+suffix
        self.other_po="PO-other-"+suffix
        self.buyer=CommercialContext("alice",self.tenant_a,frozenset({"procurement"}))
        self.reviewer=CommercialContext("bob",self.tenant_a,frozenset({"procurement_reviewer"}))
        self.foreign=CommercialContext("charlie",self.tenant_b,frozenset({"procurement"}))
        with self.connect() as db:
            for tenant,po in [(self.tenant_a,self.po),(self.tenant_b,self.other_po)]:
                db.execute(
                    """INSERT INTO procurement_pos
                       (tenant_id,po_id,supplier_id,quantity,contract_unit_price,currency)
                       VALUES (%s,%s,%s,%s,%s,'USD')""",
                    (tenant,po,"vendor-1",2,Decimal("50.00")))
                db.execute(
                    """INSERT INTO procurement_invoices
                       (tenant_id,invoice_id,po_id,invoice_total)
                       VALUES (%s,%s,%s,%s)""",
                    (tenant,"INV-"+po,po,Decimal("105.00")))
                db.execute(
                    """INSERT INTO procurement_certificates
                       (tenant_id,supplier_id,certificate_id,expires_on)
                       VALUES (%s,%s,%s,%s)""",
                    (tenant,"vendor-1","cert-"+po,date.today()-timedelta(days=2)))
                db.execute(
                    """INSERT INTO procurement_knowledge
                       (tenant_id,source_id,po_id,doc_type,source_version,source_uri,
                        classification,authorized_roles,content,content_sha256,approved_at)
                       VALUES (%s,%s,%s,'contract',1,%s,'synthetic',%s,%s,%s,now())""",
                    (tenant,"doc-"+po,po,"urn:lsk:synthetic:doc-"+po,
                     ["procurement","procurement_reviewer"],
                     "Synthetic invoice contract difference policy for procurement review.",
                     "0"*64))

    def test_tenant_scoped_business_and_document_reads(self):
        a=self.repo.case(self.buyer,self.po)
        self.assertEqual(a["tenant_id"],self.tenant_a)
        self.assertEqual(Decimal(ensure_case(a,tenant_id=self.tenant_a,po_id=self.po)["variance"]),Decimal("5"))
        self.assertEqual(self.repo.evidence(self.buyer,self.po,"invoice")[0]["po_id"],self.po)
        self.assertEqual(self.repo.evidence(self.foreign,self.po,"invoice"),[])
        with self.assertRaises(LookupError):
            self.repo.case(self.foreign,self.po)

    def test_document_role_acl_applied_before_search(self):
        with self.connect() as db:
            db.execute(
                """INSERT INTO procurement_knowledge
                   (tenant_id,source_id,po_id,doc_type,source_version,source_uri,
                    classification,authorized_roles,content,content_sha256,approved_at)
                   VALUES (%s,%s,%s,'certificate',1,%s,'synthetic',%s,%s,%s,now())""",
                (self.tenant_a,"restricted-"+self.po,self.po,
                 "urn:lsk:synthetic:restricted-"+self.po,
                 ["procurement_reviewer"],
                 "Private certificate invoice review record only for reviewer.","a"*64))
        buyer=self.repo.evidence(self.buyer,self.po,"invoice")
        reviewer=self.repo.evidence(self.reviewer,self.po,"invoice")
        self.assertEqual(len(buyer),1)
        self.assertEqual(len(reviewer),2)
        self.assertEqual(self.repo.evidence(self.buyer,self.po,"nonexistentphrase"),[])

    def test_idempotent_pending_exception_and_separate_review(self):
        finding=ensure_case(self.repo.case(self.buyer,self.po),
                            tenant_id=self.tenant_a,po_id=self.po)
        first=self.repo.create_exception(self.buyer,self.po,"same-key",finding)
        repeated=self.repo.create_exception(self.buyer,self.po,"same-key",finding)
        self.assertEqual(first["exception_id"],repeated["exception_id"])
        self.assertEqual(first["status"],"pending")
        with self.assertRaises(PermissionError):
            self.repo.decide(self.buyer,first["exception_id"],"approved")
        with self.assertRaises(LookupError):
            self.repo.decide(CommercialContext("alice",self.tenant_a,frozenset({"procurement_reviewer"})),
                             first["exception_id"],"approved")
        with self.assertRaises(PermissionError):
            self.repo.decide(self.foreign,first["exception_id"],"approved")
        decision=self.repo.decide(self.reviewer,first["exception_id"],"approved")
        self.assertEqual(decision["status"],"approved")
        self.assertFalse(decision["erp_updated"])
        with self.assertRaises(LookupError):
            self.repo.decide(self.reviewer,first["exception_id"],"approved")
        with self.connect() as db:
            events=db.execute(
                """SELECT outcome FROM audit WHERE tenant_id=%s AND domain='procurement'""",
                (self.tenant_a,)).fetchall()
        self.assertIn(("exception_proposed",),events)
        self.assertIn(("exception_approved",),events)

    def test_immutable_synthetic_ingestion(self):
        from phase28.fde_commercial.ingest import ingest
        doc={"tenant_id":self.tenant_a,"source_id":"ingested-"+self.po,
             "po_id":self.po,"doc_type":"contract","source_version":1,
             "source_uri":"urn:lsk:synthetic:ingested-"+self.po,
             "classification":"synthetic","authorized_roles":["procurement"],
             "content":"Approved synthetic invoice variance review clause."}
        self.assertEqual(ingest([doc],connect=self.connect),1)
        self.assertEqual(ingest([doc],connect=self.connect),1)
        changed={**doc,"content":"Altered document without new version"}
        with self.assertRaises(ValueError):
            ingest([changed],connect=self.connect)
        with self.assertRaises(ValueError):
            ingest([{**doc,"classification":"customer-confidential"}],connect=self.connect)
        with self.assertRaises(ValueError):
            ingest([{**doc,"authorized_roles":["procurement_reviewer"]}],connect=self.connect)

    def test_migration_creates_restricted_app_role(self):
        from unittest.mock import patch
        from phase28 import migrate_postgres
        suffix=uuid4().hex[:10]
        app_user="lsk_test_"+suffix
        password="test-only-random-secret-123456789-"+suffix
        with patch.dict(os.environ,{
            "LSK_APP_DB_USERNAME":app_user,
            "LSK_APP_DB_PASSWORD":password
        }), patch("phase28.migrate_postgres.database_connect",self.connect):
            migrate_postgres.main()
            migrate_postgres.main()  # rerun is idempotent, including role grants
        with psycopg.connect(host="localhost",port=5432,dbname="lsk_test",
                            user=app_user,password=password,sslmode="disable") as db:
            db.execute("SELECT source_id FROM sources WHERE tenant_id=%s",
                       (self.tenant_a,)).fetchall()
            db.execute(
                """INSERT INTO audit(id,ts,actor,tenant_id,domain,outcome)
                   VALUES (%s,now(),%s,%s,%s,%s)""",
                (uuid4().hex,"app",self.tenant_a,"procurement","test"))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                db.execute("UPDATE procurement_pos SET quantity=1 WHERE tenant_id=%s",
                           (self.tenant_a,))
