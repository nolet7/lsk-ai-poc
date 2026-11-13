"""Async integration gateway for three synthetic business microservices.

POC only: shared API key and X-Actor headers are NOT production identity.
"""
import asyncio
import os
import secrets
from urllib.parse import quote
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

DOMAINS = {
    "sales": os.getenv("SALES_SERVICE_URL", "http://localhost:8101").rstrip("/"),
    "marketing": os.getenv("MARKETING_SERVICE_URL", "http://localhost:8102").rstrip("/"),
    "finance": os.getenv("FINANCE_SERVICE_URL", "http://localhost:8103").rstrip("/"),
}
app = FastAPI(title="LSK Enterprise AI Enablement Gateway", version="1.0.0")

def identity(x_api_key: str | None = Header(default=None),
             x_actor: str | None = Header(default=None)):
    key = os.getenv("GATEWAY_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="GATEWAY_API_KEY not configured")
    if not x_api_key or not secrets.compare_digest(key, x_api_key):
        raise HTTPException(status_code=401, detail="Invalid gateway key")
    if not x_actor or not x_actor.strip() or len(x_actor) > 80:
        raise HTTPException(status_code=400, detail="X-Actor required")
    return x_actor.strip()

def service_url(domain: str) -> str:
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail="Unknown business application")
    return DOMAINS[domain]

async def forward(domain: str, path: str, actor: str, method: str = "GET",
                  payload: dict | None = None, reviewer: bool = False,
                  client: httpx.AsyncClient | None = None):
    url = service_url(domain) + path
    key = os.getenv("DEMO_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="DEMO_API_KEY not configured")
    headers = {"X-API-Key": key, "X-Actor": actor}
    if reviewer:
        # Demo only: true reviewer identity must be verified through OIDC before production.
        headers["X-Role"] = "reviewer"
    async def request(c):
        response = await c.request(method, url, headers=headers, json=payload)
        try:
            content = response.json()
        except ValueError:
            raise HTTPException(status_code=502, detail="Malformed business application response")
        if response.is_error:
            raise HTTPException(status_code=response.status_code, detail=content.get("detail", "Upstream error") if isinstance(content, dict) else "Upstream error")
        return content
    try:
        if client is not None:
            return await request(client)
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as session:
            return await request(session)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Business service unavailable") from exc

class Proposal(BaseModel):
    record_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=3, max_length=1000)
    reason: str = Field(min_length=3, max_length=500)

class Decision(BaseModel):
    approve: bool

@app.get("/health")
async def health():
    return {"status": "ok", "services": list(DOMAINS)}

@app.get("/v1/apps")
async def apps(actor: str = Depends(identity)):
    """Discover services concurrently; individual failures are reported, not hidden."""
    results = await asyncio.gather(
        *(forward(domain, "/v1/capabilities", actor) for domain in DOMAINS),
        return_exceptions=True,
    )
    response = {}
    for domain, result in zip(DOMAINS, results):
        response[domain] = {"status": "unavailable"} if isinstance(result, Exception) else {"status": "available", "capabilities": result}
    return response

@app.get("/v1/apps/{domain}/records")
async def records(domain: str, actor: str = Depends(identity)):
    return await forward(domain, "/v1/records", actor)

@app.get("/v1/apps/{domain}/records/{record_id}/insight")
async def insight(domain: str, record_id: str, actor: str = Depends(identity)):
    return await forward(domain, "/v1/records/" + quote(record_id, safe="") + "/insight", actor)

@app.get("/v1/apps/{domain}/proposals")
async def proposals(domain: str, actor: str = Depends(identity)):
    return await forward(domain, "/v1/proposals", actor)

@app.post("/v1/apps/{domain}/proposals", status_code=201)
async def propose(domain: str, payload: Proposal, actor: str = Depends(identity)):
    return await forward(domain, "/v1/proposals", actor, "POST", payload.model_dump())

@app.post("/v1/apps/{domain}/proposals/{proposal_id}/decision")
async def decide(domain: str, proposal_id: str, payload: Decision,
                 x_role: str | None = Header(default=None),
                 actor: str = Depends(identity)):
    if x_role != "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer role required (demo only)")
    return await forward(domain, "/v1/proposals/" + quote(proposal_id, safe="") + "/decision", actor,
                         "POST", payload.model_dump(), reviewer=True)

@app.get("/v1/apps/{domain}/audit")
async def audit(domain: str, x_role: str | None = Header(default=None), actor: str = Depends(identity)):
    if x_role != "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer role required (demo only)")
    return await forward(domain, "/v1/audit", actor, reviewer=True)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LSK AI Hub</title>
<style>body{font:16px system-ui;max-width:850px;margin:50px auto;padding:20px;background:#f6f8fa;color:#1c3450}
a{color:#1764a5}article{background:white;border-radius:10px;padding:20px;margin:16px 0;border:1px solid #d8e2ec}</style>
</head><body><h1>LSK Enterprise AI Enablement Hub</h1><p>Local synthetic-data business services with a common API contract.</p>
<article><h2>Sales Account Intelligence</h2><a href="http://localhost:8101/portal">Open Sales Portal</a></article>
<article><h2>Marketing Intelligence</h2><a href="http://localhost:8102/portal">Open Marketing Portal</a></article>
<article><h2>Finance Exception Review</h2><a href="http://localhost:8103/portal">Open Finance Portal</a></article>
<p>Developer API: <a href="/docs">Gateway Swagger docs</a>. Synthetic demo only, not enterprise SSO.</p></body></html>"""
