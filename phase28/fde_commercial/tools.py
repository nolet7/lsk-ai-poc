"""Trusted in-process tool adapter for offline integration tests.

Production uses the authenticated remote MCP adapter; tests can inject this
adapter with a fake repository. Never let a model construct CommercialContext.
"""
from __future__ import annotations
from phase28.fde_commercial.contracts import CommercialContext

class InProcessTools:
    def __init__(self, repository):
        self.repository = repository

    async def case(self, ctx: CommercialContext, po_id: str):
        return self.repository.case(ctx, po_id)

    async def evidence(self, ctx: CommercialContext, po_id: str, query: str):
        return self.repository.evidence(ctx, po_id, query)
