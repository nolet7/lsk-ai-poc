"""Strict request/response shapes and fail-closed policy checks."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    po_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    question: str = Field(min_length=3, max_length=2000)
    use_model: bool = False
    propose_exception: bool = False
    idempotency_key: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
    )

class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern=r"^(approved|rejected)$")

@dataclass(frozen=True)
class CommercialContext:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    raw_token: str = ""

def ensure_case(case: dict[str, Any], *, tenant_id: str, po_id: str) -> dict[str, Any]:
    """Reject untrusted MCP responses instead of trusting tenant and business values."""
    if not isinstance(case, dict) or case.get("tenant_id") != tenant_id or case.get("po_id") != po_id:
        raise ValueError("Unauthorized or malformed business result")
    required = {"supplier_id", "quantity", "contract_unit_price", "invoice_total",
                "currency", "certificate_expiry", "invoice_id"}
    if not required.issubset(case):
        raise ValueError("Missing authoritative business fields")
    for field in ("supplier_id", "invoice_id", "currency"):
        if not isinstance(case[field], str) or not case[field] or len(case[field]) > 128:
            raise ValueError("Malformed business field")
    try:
        qty = Decimal(str(case["quantity"]))
        unit = Decimal(str(case["contract_unit_price"]))
        invoice = Decimal(str(case["invoice_total"]))
        if any(not x.is_finite() for x in (qty, unit, invoice)) or qty <= 0 or unit < 0 or invoice < 0:
            raise ValueError
        expiry = date.fromisoformat(case["certificate_expiry"])
    except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
        raise ValueError("Invalid commercial figures") from exc
    expected = qty * unit
    return {"po_id": po_id, "invoice_id": case["invoice_id"],
            "supplier_id": case["supplier_id"], "currency": case["currency"],
            "expected_total": str(expected), "invoice_total": str(invoice),
            "variance": str(invoice - expected),
            "price_mismatch": invoice != expected,
            "certificate_expired": expiry < date.today(),
            "certificate_expiry": str(expiry)}

def ensure_evidence(evidence: list[dict], *, tenant_id: str, po_id: str) -> list[dict]:
    if not isinstance(evidence, list) or len(evidence) > 10:
        raise ValueError("Invalid evidence volume")
    seen = set()
    out = []
    for doc in evidence:
        if not isinstance(doc, dict) or doc.get("tenant_id") != tenant_id or doc.get("po_id") != po_id:
            raise ValueError("Cross-tenant evidence returned by tool")
        sid, content = doc.get("source_id"), doc.get("content")
        if (not isinstance(sid, str) or not sid or len(sid) > 128 or sid in seen or
                not isinstance(content, str) or not content or len(content) > 5000):
            raise ValueError("Invalid or duplicate source")
        seen.add(sid)
        out.append({"id": sid, "content": content})
    return out
