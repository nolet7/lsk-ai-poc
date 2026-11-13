"""Grounded account briefs: real LLM inference when configured, transparent fallback otherwise."""
import json
import os
from urllib import error, request

def deterministic_brief(account):
    risk = "Close date approaching; confirm next steps." if account["stage"] in ("Renewal", "Negotiation") else "Qualification not complete."
    return {
        "account_id":account["id"], "summary": f'{account["name"]} is in {account["stage"]} with a ${account["amount"]:,} opportunity.',
        "risks":[risk], "recommended_actions":["Confirm outstanding buyer questions","Schedule the next owner-approved follow-up"],
        "evidence":[{"field":"stage","value":account["stage"]},{"field":"notes","value":account["notes"]}],
        "mode":"deterministic", "model":None
    }

def account_brief(account):
    """Do not silently claim AI inference when no configured model exists."""
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return deterministic_brief(account)
    model=os.getenv("SALES_LLM_MODEL","gpt-4.1-mini")
    payload={
        "model":model,"temperature":0,
        "messages":[
            {"role":"system","content":"You are an internal sales analyst. Use ONLY the account JSON. Return a JSON object with exactly: summary (string), risks (array of strings), recommended_actions (array of strings). Do not invent facts, dates, or contacts. Never execute any actions."},
            {"role":"user","content":json.dumps(account)}
        ],
        "response_format":{"type":"json_object"}
    }
    endpoint=os.getenv("SALES_LLM_ENDPOINT","https://api.openai.com/v1/chat/completions")
    if not endpoint.startswith("https://"):
        raise ValueError("SALES_LLM_ENDPOINT must use HTTPS")
    req=request.Request(endpoint,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
        with request.urlopen(req,timeout=20) as response:
            body=json.loads(response.read())
        generated=json.loads(body["choices"][0]["message"]["content"])
        if not isinstance(generated.get("summary"),str) or not isinstance(generated.get("risks"),list) or not isinstance(generated.get("recommended_actions"),list):
            raise ValueError("Model response violates required schema")
        if not all(isinstance(v,str) for v in generated["risks"]+generated["recommended_actions"]):
            raise ValueError("Model lists must contain only strings")
    except (error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError("LLM inference failed; request not completed") from exc
    return {"account_id":account["id"],"summary":generated["summary"],"risks":generated["risks"],"recommended_actions":generated["recommended_actions"],
            "evidence":[{"field":"stage","value":account["stage"]},{"field":"notes","value":account["notes"]}],"mode":"llm","model":model}
