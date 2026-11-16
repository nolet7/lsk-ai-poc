"""Enterprise-boundary reference endpoints for synthetic LSK commercial data.

The API layer authorizes callers; retrieval checks ACL before model context;
business services own authoritative numbers; model gateway is read-only.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from .acl_retrieval import retrieve
from .bedrock_gateway import infer, ModelUnavailable
from .command_store import submit, my_proposals
from .enterprise_policy import scope_for, require_demo_proposals, DOMAINS

router=APIRouter(prefix="/v1/platform",tags=["Governed LSK AI (synthetic POC)"])

class Ask(BaseModel):
    question: str = Field(min_length=3,max_length=2000)
    domain: str
    record_id: str | None = Field(default=None,max_length=100)
    use_model: bool = True

class Proposal(BaseModel):
    domain: str
    record_id: str = Field(min_length=1,max_length=100)
    text: str = Field(min_length=3,max_length=1000)
    reason: str = Field(min_length=3,max_length=500)

def install(app, identity, forward):
    @router.post("/ask")
    async def ask(body: Ask, actor: str = Depends(identity)):
        scope = scope_for(actor,body.domain)
        if body.domain not in scope.domains:
            raise HTTPException(403,"Business domain not authorized")
        sources=retrieve(body.question,scope)
        evidence={"sources":sources, "tenant":scope.tenant, "domain":body.domain}
        if body.record_id:
            if not body.record_id.replace("-","").replace("_","").isalnum():
                raise HTTPException(422,"Unsupported record identifier")
            from urllib.parse import quote
            detail=await forward(body.domain,"/v1/records/"+quote(body.record_id,safe="")+"/insight",actor)
            evidence["business_record"]=detail
        if not sources and not body.record_id:
            return {"mode":"no_verified_evidence","answer":"No authorized evidence found.",
                    "sources":[],"actions_taken":[]}
        if not body.use_model:
            return {"mode":"retrieval-only","evidence":evidence,"actions_taken":[]}
        try:
            return await infer(body.question,evidence)
        except ModelUnavailable as exc:
            raise HTTPException(503,str(exc)) from exc

    @router.post("/proposals",status_code=201)
    async def propose(body: Proposal, idempotency_key: str | None=Header(default=None),
                      actor: str=Depends(identity)):
        scope=scope_for(actor,body.domain)
        require_demo_proposals()
        if body.domain not in DOMAINS:
            raise HTTPException(404,"Unknown business domain")
        if not body.record_id.replace("-","").replace("_","").isalnum():
            raise HTTPException(422,"Invalid record identifier")
        if not idempotency_key:
            raise HTTPException(400,"Idempotency-Key required")
        try:
            return submit(tenant=scope.tenant,actor=actor,domain=body.domain,
                          record_id=body.record_id,text=body.text,reason=body.reason,
                          idempotency_key=idempotency_key)
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc

    @router.get("/proposals")
    async def list_proposals(actor: str=Depends(identity)):
        scope=scope_for(actor)
        return {"items":my_proposals(scope.tenant,actor)}

    app.include_router(router)
