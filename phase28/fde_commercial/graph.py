"""Bounded LangGraph workflow. The LLM cannot choose arbitrary tools or approve writes."""
from __future__ import annotations
from typing import Any, Protocol, TypedDict
from langgraph.graph import StateGraph, START, END

from phase28.fde_commercial.contracts import CommercialContext, ensure_case, ensure_evidence

class ReadTools(Protocol):
    async def case(self, ctx: CommercialContext, po_id: str) -> dict: ...
    async def evidence(self, ctx: CommercialContext, po_id: str) -> list[dict]: ...

class State(TypedDict, total=False):
    ctx: CommercialContext
    po_id: str
    question: str
    case: dict
    findings: dict
    evidence: list[dict]
    outcome: str
    steps: int

class CommercialGraph:
    def __init__(self, tools: ReadTools):
        self.tools = tools
        graph = StateGraph(State)
        graph.add_node("read_authoritative", self._read)
        graph.add_node("validate_financials", self._validate)
        graph.add_node("retrieve_authorized", self._retrieve)
        graph.add_node("finish", self._finish)
        graph.add_edge(START, "read_authoritative")
        graph.add_edge("read_authoritative", "validate_financials")
        graph.add_edge("validate_financials", "retrieve_authorized")
        graph.add_edge("retrieve_authorized", "finish")
        graph.add_edge("finish", END)
        self._graph = graph.compile()

    async def _read(self, state: State) -> dict:
        ctx = state["ctx"]
        case = await self.tools.case(ctx, state["po_id"])
        if not isinstance(case, dict):
            raise ValueError("Malformed tool response")
        return {"case": case, "steps": 1}

    async def _validate(self, state: State) -> dict:
        from phase28.fde_commercial.contracts import ensure_case
        findings = ensure_case(state["case"],tenant_id=state["ctx"].tenant_id,po_id=state["po_id"])
        return {"findings": findings, "steps": state["steps"]+1}

    async def _retrieve(self, state: State) -> dict:
        docs = await self.tools.evidence(state["ctx"], state["po_id"])
        return {"evidence": ensure_evidence(docs, tenant_id=state["ctx"].tenant_id, po_id=state["po_id"]),
                "steps": state["steps"]+1}

    async def _finish(self, state: State) -> dict:
        # No model action or database write is performed by the graph.
        return {"outcome": "investigated", "steps": state["steps"]+1}

    async def run(self, ctx: CommercialContext, po_id: str, question: str) -> State:
        if len(question)>2000 or not question:
            raise ValueError("Invalid question")
        result = await self._graph.ainvoke({"ctx":ctx,"po_id":po_id,"question":question,"steps":0},
                                         config={"recursion_limit":8})
        if result["steps"] != 4:
            raise RuntimeError("Unexpected execution count")
        return result
