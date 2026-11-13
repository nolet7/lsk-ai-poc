"""FastAPI business workflow. Synthetic accounts only; no external CRM writes."""
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sales_enablement import intelligence, store

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.initialize()
    yield

app = FastAPI(title="LSK Sales AI Enablement Demo",version="0.1.0",lifespan=lifespan)

def identity(x_api_key: str | None=Header(default=None), x_actor: str | None=Header(default=None)):
    key=os.getenv("SALES_DEMO_API_KEY")
    if not key:
        raise HTTPException(503,"Set SALES_DEMO_API_KEY to enable the demo API")
    if not x_api_key or not secrets.compare_digest(x_api_key,key):
        raise HTTPException(401,"Invalid API key")
    if not x_actor or not x_actor.strip() or len(x_actor)>80:
        raise HTTPException(400,"X-Actor header is required")
    return x_actor.strip()

def reviewer(x_role: str | None=Header(default=None), actor: str=Depends(identity)):
    # Demo-only header roles are not a substitute for SSO/JWT-verified identity.
    if x_role!="reviewer":
        raise HTTPException(403,"Reviewer role required")
    return actor

class ChangeRequest(BaseModel):
    account_id: str=Field(min_length=1,max_length=100)
    proposed_note: str=Field(min_length=3,max_length=1000)
    reason: str=Field(min_length=3,max_length=500)

class Decision(BaseModel):
    approve: bool

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/accounts")
def accounts(actor: str=Depends(identity)):
    return store.list_accounts()

@app.get("/accounts/{account_id}/brief")
def brief(account_id: str,actor: str=Depends(identity)):
    account=store.get_account(account_id)
    if not account:
        raise HTTPException(404,"Account not found")
    try:
        return intelligence.account_brief(account)
    except RuntimeError as exc:
        raise HTTPException(502,str(exc)) from exc

@app.post("/change-requests",status_code=201)
def create_change(payload: ChangeRequest,actor: str=Depends(identity)):
    try:
        return store.request_change(payload.account_id,payload.proposed_note,payload.reason,actor)
    except KeyError:
        raise HTTPException(404,"Account not found")

@app.get("/change-requests")
def change_requests(actor: str=Depends(identity)):
    return store.list_approvals()

@app.post("/change-requests/{approval_id}/decision")
def decide(approval_id: str,payload: Decision,actor: str=Depends(reviewer)):
    try:
        return store.decide(approval_id,actor,payload.approve)
    except KeyError:
        raise HTTPException(404,"Approval not found")
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc

@app.get("/audit-events")
def audit_events(actor: str=Depends(reviewer)):
    return store.list_events()
