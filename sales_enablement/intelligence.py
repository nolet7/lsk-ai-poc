"""Grounded account briefs with asynchronous HTTP model inference."""
import json
import os

import httpx

def deterministic_brief(account):
    risk = "Close date approaching; confirm next steps." if account["stage"] in ("Renewal", "Negotiation") else "Qualification not complete."
    return {
        "account_id": account["id"],
        "summary": f'{account["name"]} is in {account["stage"]} with a ${account["amount"]:,} opportunity.',
        "risks": [risk],
        "recommended_actions": ["Confirm outstanding buyer questions", "Schedule the next owner-approved follow-up"],
        "evidence": [{"field": "stage", "value": account["stage"]}, {"field": "notes", "value": account["notes"]}],
        "mode": "deterministic",
        "model": None,
    }

async def account_brief(account, client: httpx.AsyncClient | None = None):
    """Call an LLM without blocking the ASGI event loop; never silently fake model results."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return deterministic_brief(account)
    model = os.getenv("SALES_LLM_MODEL", "gpt-4.1-mini")
    endpoint = os.getenv("SALES_LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    # Prevent arbitrary HTTP endpoints. Custom endpoints should be reviewed before use in a deployment.
    if not endpoint.startswith("https://"):
        raise ValueError("SALES_LLM_ENDPOINT must use HTTPS")
    payload = {
        "model": model, "temperature": 0,
        "messages": [
            {"role": "system", "content": "You are an internal sales analyst. Use ONLY the account JSON. Return a JSON object with exactly: summary (string), risks (array of strings), recommended_actions (array of strings). Do not invent facts, dates, or contacts. Never execute any actions."},
            {"role": "user", "content": json.dumps(account)},
        ],
        "response_format": {"type": "json_object"},
    }
    async def execute(c: httpx.AsyncClient):
        response = await c.post(endpoint, json=payload, headers={"Authorization": "Bearer " + key})
        response.raise_for_status()
        data = response.json()
        return json.loads(data["choices"][0]["message"]["content"])
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=False) as temp:
                generated = await execute(temp)
        else:
            generated = await execute(client)
        if not isinstance(generated, dict):
            raise ValueError("Model response must be an object")
        if not isinstance(generated.get("summary"), str):
            raise ValueError("Invalid summary")
        if not all(isinstance(generated.get(field), list) and all(isinstance(x, str) for x in generated[field]) for field in ("risks", "recommended_actions")):
            raise ValueError("Invalid list fields")
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("LLM inference failed; request not completed") from exc
    return {
        "account_id": account["id"], "summary": generated["summary"],
        "risks": generated["risks"], "recommended_actions": generated["recommended_actions"],
        "evidence": [{"field": "stage", "value": account["stage"]}, {"field": "notes", "value": account["notes"]}],
        "mode": "llm", "model": model,
    }
