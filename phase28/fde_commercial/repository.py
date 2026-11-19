"""Read-only PostgreSQL tool handlers and separate human-only exception review.

All queries constrain tenant_id; caller identity is provided ONLY by a verified
OIDC boundary. This is a synthetic lab adapter, not a direct ERP integration.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import psycopg
from phase28.fde_commercial.contracts import CommercialContext

class ProcurementRepository:
    def __init__(self, connect):
        self.connect = connect

    def _require_procurement(self, ctx: CommercialContext) -> None:
        if not ctx.roles.intersection({"procurement", "procurement_reviewer"}):
            raise PermissionError("Procurement access required")

    def case(self, ctx: CommercialContext, po_id: str) -> dict[str, Any]:
        self._require_procurement(ctx)
        with self.connect() as db:
            row = db.execute(
                """SELECT p.po_id,p.tenant_id,p.supplier_id,p.quantity,
                          p.contract_unit_price,p.currency,i.invoice_id,i.invoice_total,
                          c.expires_on
                   FROM procurement_pos p
                   JOIN procurement_invoices i ON i.tenant_id=p.tenant_id AND i.po_id=p.po_id
                   JOIN procurement_certificates c ON c.tenant_id=p.tenant_id AND c.supplier_id=p.supplier_id
                   WHERE p.tenant_id=%s AND p.po_id=%s
                   ORDER BY i.invoice_id,c.expires_on DESC LIMIT 1""",
                (ctx.tenant_id, po_id)).fetchone()
        if row is None:
            raise LookupError("Business record unavailable")
        return dict(zip(("po_id","tenant_id","supplier_id","quantity",
                         "contract_unit_price","currency","invoice_id",
                         "invoice_total","certificate_expiry"), row))

    def evidence(self, ctx: CommercialContext, po_id: str) -> list[dict]:
        self._require_procurement(ctx)
        with self.connect() as db:
            rows = db.execute(
                """SELECT source_id,tenant_id,record_id,content FROM sources
                   WHERE tenant_id=%s AND domain='procurement' AND record_id=%s
                   ORDER BY source_id LIMIT 10""", (ctx.tenant_id, po_id)).fetchall()
        return [{"source_id": x[0], "tenant_id": x[1], "po_id": x[2], "content": x[3]}
                for x in rows]

    def create_exception(self, ctx: CommercialContext, po_id: str, key: str,
                         findings: dict) -> dict:
        """Create a pending proposal once, atomically, with actor-scoped idempotency."""
        self._require_procurement(ctx)
        if not key:
            raise ValueError("Idempotency key required")
        if not findings.get("price_mismatch") and not findings.get("certificate_expired"):
            raise ValueError("No business exception to propose")
        fingerprint = f"{po_id}:{findings['expected_total']}:{findings['invoice_total']}:{findings['certificate_expiry']}"
        with self.connect() as db:
            row = db.execute(
                """INSERT INTO procurement_exceptions
                   (id,tenant_id,po_id,requester,idempotency_key,fingerprint,status,created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,'pending',%s)
                   ON CONFLICT (tenant_id,requester,idempotency_key) DO NOTHING
                   RETURNING id,po_id,fingerprint,status""",
                (uuid4().hex, ctx.tenant_id, po_id, ctx.subject, key,
                 fingerprint, datetime.now(timezone.utc))).fetchone()
            if row is None:
                row = db.execute(
                    """SELECT id,po_id,fingerprint,status FROM procurement_exceptions
                       WHERE tenant_id=%s AND requester=%s AND idempotency_key=%s""",
                    (ctx.tenant_id,ctx.subject,key)).fetchone()
            if row is None or row[1] != po_id or row[2] != fingerprint:
                raise ValueError("Idempotency key reused for different request")
            db.execute(
                """INSERT INTO audit(id,ts,actor,tenant_id,domain,outcome)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (uuid4().hex,datetime.now(timezone.utc),ctx.subject,
                 ctx.tenant_id,"procurement","exception_proposed"))
        if row[1] != po_id or row[2] != fingerprint:
            raise ValueError("Idempotency key reused for different request")
        return {"exception_id": row[0], "status": row[3]}

    def decide(self, ctx: CommercialContext, exception_id: str, decision: str) -> dict:
        """Independent reviewer only. No ERP modification on approval."""
        if "procurement_reviewer" not in ctx.roles:
            raise PermissionError("Reviewer role required")
        with self.connect() as db:
            row = db.execute(
                """UPDATE procurement_exceptions
                   SET status=%s, reviewer=%s, reviewed_at=%s
                   WHERE tenant_id=%s AND id=%s AND status='pending' AND requester<>%s
                   RETURNING id,status""",
                (decision,ctx.subject,datetime.now(timezone.utc),
                 ctx.tenant_id,exception_id,ctx.subject)).fetchone()
            if row is not None:
                db.execute(
                    """INSERT INTO audit(id,ts,actor,tenant_id,domain,outcome)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (uuid4().hex,datetime.now(timezone.utc),ctx.subject,
                     ctx.tenant_id,"procurement","exception_"+decision))
        if row is None:
            raise LookupError("Pending exception unavailable or self-review forbidden")
        return {"exception_id": row[0], "status": row[1], "erp_updated": False}
