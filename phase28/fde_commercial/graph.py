"""Bounded procurement LangGraph with role-filtered lexical RAG and one safe retry.

No LLM-generated tool names, no arbitrary SQL, no business mutations.
"""
from __future__ import annotations

from typing import Protocol, TypedDict
from langgraph.graph import StateGraph, START, END

from phase28.fde_commercial.contracts import CommercialContext, ensure_case, ensure_evidence


class ReadTools(Protocol):
    async def case(self, ctx: CommercialContext, po_id: str) -> dict: ...
    async def evidence(self, ctx: CommercialContext, po_id: str, query: str) -> list[dict]: ...


class State(TypedDict, total=False):
    ctx: CommercialContext
    po_id: str
    question: str
    search_query: str
    case: dict
    findings: dict
    evidence: list[dict]
    need_retry: bool
    retries: int
    outcome: str
    steps: int


class CommercialGraph:
    def __init__(self, tools: ReadTools):
        self.tools = tools
        graph = StateGraph(State)
        graph.add_node("read_authoritative", self._read)
        graph.add_node("validate_financials", self._validate)
        graph.add_node("retrieve_authorized", self._retrieve)
        graph.add_node("assess_relevance", self._assess)
        graph.add_node("refine_query", self._refine)
        graph.add_node("finish", self._finish)
        graph.add_edge(START, "read_authoritative")
        graph.add_edge("read_authoritative", "validate_financials")
        graph.add_edge("validate_financials", "retrieve_authorized")
        graph.add_edge("retrieve_authorized", "assess_relevance")
        graph.add_conditional_edges("assess_relevance", self._route,
                                    {"refine_query":"refine_query","finish":"finish"})
        graph.add_edge("refine_query", "retrieve_authorized")
        graph.add_edge("finish", END)
        self._graph=graph.compile()

    async def _read(self,state:State)->dict:
        case=await self.tools.case(state["ctx"],state["po_id"])
        if not isinstance(case,dict):
            raise ValueError("Malformed MCP business result")
        return {"case":case,"steps":1}

    async def _validate(self,state:State)->dict:
        finding=ensure_case(state["case"],tenant_id=state["ctx"].tenant_id,
                            po_id=state["po_id"])
        return {"findings":finding,"steps":state["steps"]+1}

    async def _retrieve(self,state:State)->dict:
        docs=await self.tools.evidence(state["ctx"],state["po_id"],state["search_query"])
        return {"evidence":ensure_evidence(docs,tenant_id=state["ctx"].tenant_id,
                                           po_id=state["po_id"]),
                "steps":state["steps"]+1}

    async def _assess(self,state:State)->dict:
        return {"need_retry":not bool(state["evidence"]) and state.get("retries",0)<1,
                "steps":state["steps"]+1}

    def _route(self,state:State)->str:
        return "refine_query" if state.get("need_retry") else "finish"

    async def _refine(self,state:State)->dict:
        # Bounded domain-specific fallback, NOT an LLM-selected arbitrary search query.
        return {"search_query":"invoice contract certificate supplier policy",
                "retries":state.get("retries",0)+1,
                "steps":state["steps"]+1}

    async def _finish(self,state:State)->dict:
        return {"outcome":"investigated" if state["evidence"] else "no_relevant_document",
                "steps":state["steps"]+1}

    async def run(self,ctx:CommercialContext,po_id:str,question:str)->State:
        if not isinstance(question,str) or not 3<=len(question)<=2000:
            raise ValueError("Invalid question")
        result=await self._graph.ainvoke({
            "ctx":ctx,"po_id":po_id,"question":question,
            "search_query":question[:256],"retries":0,"steps":0
        },config={"recursion_limit":12})
        if result["steps"] not in (5,8) or result.get("retries",0)>1:
            raise RuntimeError("Unexpected agent execution path")
        return result
