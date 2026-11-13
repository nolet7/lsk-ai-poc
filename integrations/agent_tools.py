"""Safe async integration functions callable from LangGraph agents.

These functions are an adapter; they are NOT registered in the legacy report graph.
An agent may research and propose changes but cannot approve them.
"""
import os
from urllib.parse import quote
import httpx

ALLOWED = frozenset(("sales", "marketing", "finance"))

async def _request(path: str, method: str = "GET", body: dict | None = None,
                   actor: str = "platform.agent", client: httpx.AsyncClient | None = None):
    key = os.getenv("GATEWAY_API_KEY")
    if not key:
        raise RuntimeError("Set GATEWAY_API_KEY; no business call was made")
    url = os.getenv("GATEWAY_URL", "http://localhost:8090").rstrip("/") + path
    headers = {"X-API-Key": key, "X-Actor": actor}
    async def run(c):
        response = await c.request(method, url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    if client is not None:
        return await run(client)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as session:
        return await run(session)

def _domain(domain: str):
    if domain not in ALLOWED:
        raise ValueError("Unsupported business domain")
    return domain

async def list_business_records(domain: str, *, actor: str = "platform.agent", client=None):
    """Read approved synthetic-domain records; never modifies a business system."""
    return await _request(f"/v1/apps/{_domain(domain)}/records", actor=actor, client=client)

async def generate_business_insight(domain: str, record_id: str, *, actor: str = "platform.agent", client=None):
    """Retrieve grounded business facts and optional LLM explanation."""
    return await _request(f"/v1/apps/{_domain(domain)}/records/{quote(record_id, safe='')}/insight",
                          actor=actor, client=client)

async def propose_business_change(domain: str, record_id: str, text: str, reason: str, *,
                                  actor: str = "platform.agent", client=None):
    """Create a proposal pending independent human review. This never approves it."""
    if not text.strip() or not reason.strip():
        raise ValueError("Proposal text and reason are required")
    return await _request(f"/v1/apps/{_domain(domain)}/proposals", "POST",
                          {"record_id": record_id, "text": text, "reason": reason},
                          actor=actor, client=client)
