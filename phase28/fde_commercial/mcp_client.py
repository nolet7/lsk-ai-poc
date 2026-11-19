"""Authenticated MCP Streamable HTTP client. One session per request, no shared identity."""
from __future__ import annotations
import json
from urllib.parse import urlsplit
from phase28.fde_commercial.contracts import CommercialContext

def validate_url(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or not parsed.path.endswith("/mcp")):
        raise ValueError("Private HTTPS MCP URL required")
    # URL is operator configuration, never user-controlled. Network allowlisting is additional.
    return url

class MCPTools:
    def __init__(self, url: str):
        self.url = validate_url(url)

    async def _call(self, ctx: CommercialContext, tool: str, arguments: dict):
        if not ctx.raw_token:
            raise PermissionError("Cannot call MCP without user token")
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        # New session per request: no cross-user auth header or tool state reuse.
        async with streamablehttp_client(
            self.url, headers={"Authorization": "Bearer " + ctx.raw_token},
            timeout=10.0, sse_read_timeout=20.0
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
        if result.isError:
            raise RuntimeError("MCP tool unavailable")
        obj = getattr(result, "structuredContent", None)
        if isinstance(obj, dict):
            return obj
        texts = [x.text for x in result.content if getattr(x, "type", None) == "text"]
        if len(texts) != 1 or len(texts[0]) > 20000:
            raise ValueError("Unexpected MCP result format")
        return json.loads(texts[0])

    async def case(self, ctx: CommercialContext, po_id: str) -> dict:
        return await self._call(ctx, "procurement_case_read", {"po_id": po_id})

    async def evidence(self, ctx: CommercialContext, po_id: str, query: str) -> list[dict]:
        result = await self._call(ctx, "procurement_document_search", {"po_id": po_id, "query": query})
        if not isinstance(result, dict) or set(result) != {"documents"}:
            raise ValueError("Unexpected evidence tool response")
        return result["documents"]
