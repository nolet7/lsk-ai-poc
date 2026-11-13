"""Read-only, outcome-based Bedrock commercial AI evaluation runner.

Requires running localhost gateway and authorized model access. Sends no writes
and does not report target metrics as achieved until real outputs are captured.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"evaluation"/"fixtures"/"asr_golden.json"
RESULTS=ROOT/"evaluation"/"results"

def grade_case(case, response, elapsed):
    answer=response.get("answer","")
    traces=response.get("tool_trace",[])
    successful=[t for t in traces if t.get("status")=="success" and t.get("tool") in ("get_insight","list_records")]
    record_refs={t.get("record_id") for t in successful if t.get("record_id")}
    missing=[rid for rid in case["required_record_ids"] if rid not in answer or rid not in record_refs]
    forbidden=[p for p in case.get("forbidden_phrases",[]) if p.lower() in answer.lower()]
    checks={
        "grounded_tool_read":bool(successful),
        "required_record_id_referenced":not missing,
        "forbidden_phrases_absent":not forbidden,
        "finished_with_answer":response.get("finish_reason")=="completed",
        "proposals_disabled":response.get("proposal_creation_enabled") is False,
        "no_mutation_tools":not any(t.get("tool")=="propose_change" for t in traces),
    }
    return {"case_id":case["id"],"passed":all(checks.values()),"checks":checks,
            "missing_records":missing,"forbidden_found":forbidden,
            "latency_seconds":round(elapsed,3),"model":response.get("model"),
            "mode":response.get("mode"),"finish_reason":response.get("finish_reason")}

def run():
    key=os.getenv("GATEWAY_API_KEY","")
    token=os.getenv("OIDC_ACCESS_TOKEN","")
    if not (token or key):
        raise SystemExit("Set GATEWAY_API_KEY for POC or OIDC_ACCESS_TOKEN for pilot/production")
    if os.getenv("LSK_ENABLE_DEMO_WRITES","").lower()=="true":
        raise SystemExit("Evaluation refuses to run with demo writes enabled")
    base=os.getenv("GATEWAY_URL","http://127.0.0.1:8090").rstrip("/")
    if not base.startswith("http://127.0.0.1:") and not base.startswith("http://localhost:"):
        raise SystemExit("Evaluation only allows local gateway or SSH tunnel")
    tests=json.loads(CASES.read_text(encoding="utf-8"))
    results=[]
    for case in tests:
        headers={"Content-Type":"application/json","X-Actor":"evaluation.readonly"}
        if token:
            headers["Authorization"]="Bearer "+token
        else:
            headers["X-API-Key"]=key
        payload=json.dumps({"question":case["question"],"allow_proposals":False}).encode("utf-8")
        req=urllib.request.Request(base+"/v1/agent/run",data=payload,headers=headers,method="POST")
        start=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=120) as res:
                data=json.load(res)
            result=grade_case(case,data,time.monotonic()-start)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as exc:
            result={"case_id":case["id"],"passed":False,"error":type(exc).__name__,
                    "latency_seconds":round(time.monotonic()-start,3)}
        results.append(result)
        print(case["id"], "PASS" if result["passed"] else "FAIL")
    RESULTS.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output=RESULTS/("asr_eval_"+now+".json")
    report={"timestamp":now,"total":len(results),"passed":sum(x["passed"] for x in results),
            "results":results,
            "scope":"Synthetic fixture-based model evaluations; no business adoption or production certification"}
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Evidence file:",output)
    if report["passed"] != report["total"]:
        return 1
    return 0

if __name__=="__main__":
    sys.exit(run())
