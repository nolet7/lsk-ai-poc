"""End-to-end smoke test of FOUR real FastAPI processes, without Docker or Bedrock.

Uses ephemeral ports and temporary SQLite databases. POC tests demo-key reads;
pilot/production verify they fail closed without a signed OIDC token.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
STAGE_FILE=ROOT/"integrations"/"release-stage.env"

def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]

def http(url, headers=None, body=None):
    request=urllib.request.Request(
        url, headers=headers or {},
        data=(json.dumps(body).encode() if body is not None else None),
        method=("POST" if body is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(request,timeout=8) as result:
            return result.status, json.load(result)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

def wait_ready(url, process, timeout=25):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise RuntimeError("Service process exited with status "+str(process.returncode))
        try:
            status,_=http(url+"/health")
            if status==200:
                return
        except (urllib.error.URLError,TimeoutError,ValueError):
            pass
        time.sleep(0.3)
    raise TimeoutError("Service startup health check timed out")

def run():
    lines=STAGE_FILE.read_text().splitlines()
    stages=[line.split("=",1)[1].strip() for line in lines if line.startswith("LSK_STAGE=")]
    if len(stages)!=1 or stages[0] not in ("poc","pilot","production"):
        raise RuntimeError("Invalid release stage marker")
    stage=stages[0]
    apps=("sales","marketing","finance")
    for d in apps:
        if not (ROOT/"external"/("lsk-"+("sales-account" if d=="sales" else d))/"app"/"main.py").is_file():
            raise RuntimeError("Missing application checkout: "+d)
    ports={name:port() for name in (*apps,"gateway")}
    processes=[]
    with tempfile.TemporaryDirectory(prefix="lsk-smoke-") as temp:
        folder=Path(temp)
        environment=os.environ.copy()
        environment.update({
            "GATEWAY_API_KEY":"smoke-gateway-local",
            "DEMO_API_KEY":"smoke-backend-local",
            "LSK_STAGE":stage,
            "LSK_ENABLE_DEMO_WRITES":"false",
            "OPENAI_API_KEY":"",
            "BEDROCK_MODEL_ID":"",
            "AWS_REGION":"us-east-1",
        })
        for d in apps:
            environment[d.upper()+"_SERVICE_URL"]="http://127.0.0.1:"+str(ports[d])
        try:
            for name in (*apps,"gateway"):
                cwd=ROOT if name=="gateway" else ROOT/"external"/("lsk-sales-account" if name=="sales" else "lsk-"+name)
                env={**environment,"APP_DOMAIN":name,
                     "APP_DB_PATH":str(folder/(name+".sqlite3"))}
                log=open(folder/(name+".log"),"w",encoding="utf-8")
                command=[sys.executable,"-m","uvicorn",
                         "integrations.gateway:app" if name=="gateway" else "app.main:app",
                         "--host","127.0.0.1","--port",str(ports[name])]
                proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
                processes.append((name,proc,log))
                wait_ready("http://127.0.0.1:"+str(ports[name]),proc)
            base="http://127.0.0.1:"+str(ports["gateway"])
            headers={"X-API-Key":"smoke-gateway-local","X-Actor":"smoke.employee"}
            backend_headers={"X-API-Key":"smoke-backend-local","X-Actor":"smoke.employee"}
            assert http(base+"/health")[0]==200
            for d in apps:
                back="http://127.0.0.1:"+str(ports[d])
                status,records=http(back+"/v1/records",backend_headers)
                assert status==200 and records, (d,status)
                status,_=http(back+"/v1/proposals",backend_headers,
                              {"record_id":records[0]["id"],"text":"Smoke proposal","reason":"No write allowed"})
                assert status==403, (d,status)
            if stage=="poc":
                status,discovery=http(base+"/v1/apps",headers)
                assert status==200 and set(discovery)==set(apps)
                status,records=http(base+"/v1/apps/finance/records",headers)
                assert status==200 and records
                status,insight=http(base+"/v1/apps/finance/records/inv-1002/insight",headers)
                assert status==200 and insight["mode"]=="deterministic"
                assert insight["signals"]["invoice_po_delta"]==1000
                status,_=http(base+"/v1/apps/finance/proposals",headers,
                              {"record_id":"inv-1002","text":"Smoke proposal","reason":"No write allowed"})
                assert status==403
            else:
                assert http(base+"/v1/apps",headers)[0]==401
            print("PASS: four services, read-only backend gates, stage identity, synthetic finance evidence")
        except Exception:
            for name,proc,log in processes:
                log.flush()
                path=folder/(name+".log")
                print("=== last 1000 chars of",name,"log ===",file=sys.stderr)
                print(path.read_text(encoding="utf-8")[-1000:],file=sys.stderr)
            raise
        finally:
            for _,proc,log in reversed(processes):
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill();proc.wait()
                log.close()

if __name__=="__main__":
    run()
