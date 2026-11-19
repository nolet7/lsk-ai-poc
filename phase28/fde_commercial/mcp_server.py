"""Remote read-only procurement MCP service using official MCP SDK v1.

OAuth authentication is checked again at MCP. Uses the verified caller's
tenant/roles; NEVER accepts actor, role or tenant parameters from model/tool.
"""
from __future__ import annotations
import anyio
import json
import os
from datetime import datetime, timezone
from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token
from phase28.authorization import Principal
from phase28.oidc import AuthenticationFailed, OIDCVerifier
from phase28.production_app import database_connect, load_authority
from phase28.fde_commercial.repository import ProcurementRepository
from phase28.fde_commercial.contracts import CommercialContext

class SignedOIDCVerifier:
    def __init__(self, verifier: OIDCVerifier):
        self.verifier = verifier

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            principal = self.verifier.verify(token)
        except AuthenticationFailed:
            return None
        if not any(r in principal.roles for r in ("procurement", "procurement_reviewer")):
            return None
        return AccessToken(
            token=token, client_id="lsk-commercial-agent", scopes=["procurement:read"],
            subject=principal.subject,
            claims={"tenant_id": principal.tenant_id, "roles": sorted(principal.roles)}
        )

def current_context() -> CommercialContext:
    token = get_access_token()
    if token is None or not isinstance(token.claims, dict) or "procurement:read" not in token.scopes:
        raise PermissionError("Unauthenticated MCP call")
    # Only server-side token verifier can populate claims; tool args never include tenant.
    principal = Principal(subject=token.subject, tenant_id=token.claims.get("tenant_id"),
                          roles=frozenset(token.claims.get("roles", [])))
    if not any(role in principal.roles for role in ("procurement", "procurement_reviewer")):
        raise PermissionError("Insufficient procurement authorization")
    return CommercialContext(principal.subject,principal.tenant_id,principal.roles)

def build_server(repo: ProcurementRepository | None = None):
    verifier, _ = load_authority()
    endpoint = os.environ["LSK_MCP_PUBLIC_URL"]
    if not endpoint.startswith("https://") or not endpoint.endswith("/mcp"):
        raise ValueError("Public MCP resource URL must be HTTPS /mcp")
    mcp = FastMCP(
        "LSK Procurement Read-only",
        host="0.0.0.0", port=int(os.getenv("LSK_MCP_PORT", "8082")),
        streamable_http_path="/mcp", stateless_http=True, json_response=True,
        auth=AuthSettings(issuer_url=AnyHttpUrl(os.environ["LSK_OIDC_ISSUER"]),
                          resource_server_url=AnyHttpUrl(endpoint),
                          required_scopes=["procurement:read"]),
        token_verifier=SignedOIDCVerifier(verifier)
    )
    store = repo or ProcurementRepository(database_connect)

    from starlette.responses import JSONResponse

    @mcp.custom_route("/health/ready", methods=["GET"])
    async def health(request):
        # Unaudited readiness only, intentionally no tenant or record details.
        try:
            with database_connect() as db:
                db.execute("SELECT 1").fetchone()
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)


    @mcp.tool()
    async def procurement_case_read(po_id: str) -> dict:
        """Read an approved synthetic PO, invoice and supplier certificate."""
        from phase28.fde_commercial.contracts import ensure_case
        ctx = current_context()
        case = await anyio.to_thread.run_sync(store.case, ctx, po_id)
        ensure_case(case, tenant_id=ctx.tenant_id, po_id=po_id)
        # Encode Decimal/date as JSON-safe strings without touching global identity.
        return json.loads(json.dumps(case, default=str))

    @mcp.tool()
    async def procurement_document_search(po_id: str, query: str) -> dict:
        """Search only tenant+PO-scoped procurement evidence."""
        from phase28.fde_commercial.contracts import ensure_evidence
        ctx = current_context()
        docs = await anyio.to_thread.run_sync(store.evidence, ctx, po_id, query)
        ensure_evidence(docs, tenant_id=ctx.tenant_id, po_id=po_id)
        return {"documents": docs}

    return mcp

if __name__ == "__main__":
    # Run only behind approved private TLS terminator, never internet-facing directly.
    build_server().run(transport="streamable-http")
