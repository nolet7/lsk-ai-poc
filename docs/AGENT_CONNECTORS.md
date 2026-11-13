# Business tool adapters for the LSK AI Platform

`integrations/agent_tools.py` exposes three async Python functions for authorized agent runtimes:

```python
import asyncio
from integrations.agent_tools import (
    list_business_records,
    generate_business_insight,
    propose_business_change,
)

async def demo():
    records = await list_business_records("sales")
    brief = await generate_business_insight("sales", records[0]["id"])
    proposal = await propose_business_change(
        "sales", records[0]["id"],
        "Validated account summary is ready for review",
        "Based on reviewed fictional CRM data",
    )
    print(brief["summary"], proposal["status"])

asyncio.run(demo())
```

Set `GATEWAY_URL=http://localhost:8090` and `GATEWAY_API_KEY` before running this example. The gateway and business service must be running. The adapter never approves a proposal: approval is a separate employee-facing action.

This is an **agent-callable integration adapter**. It is deliberately not plugged into the existing legacy report-generating LangGraph workflow, which is a separate use case; wiring it into a new business agent graph requires structured state, tool-selection rules, authorization, checkpoint persistence, and evaluation gates.

Business domain allow-list limits tool use to Sales, Marketing and Finance. The underlying credentials/role headers are still demo-only; never use real accounts, customer data or financial records until signed identity, scoped delegation and audit requirements are implemented.
