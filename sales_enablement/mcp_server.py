"""Optional MCP protocol server: read-only CRM tools, no write tools exposed."""
import asyncio
from sales_enablement import store, intelligence
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit("Install the optional 'mcp' package to run the MCP server") from exc

mcp=FastMCP("lsk-sales-readonly")

@mcp.tool()
def list_sales_accounts() -> list[dict]:
    """List synthetic CRM accounts (read-only)."""
    store.initialize()
    return store.list_accounts()

@mcp.tool()
async def get_sales_account_brief(account_id: str) -> dict:
    """Generate a grounded brief for a synthetic account (read-only)."""
    await asyncio.to_thread(store.initialize)
    account=await asyncio.to_thread(store.get_account, account_id)
    if account is None:
        return {"error":"Account not found"}
    return await intelligence.account_brief(account)

if __name__=="__main__":
    # Local stdio transport is for a trusted local client only.
    mcp.run()
