"""Run all four real FastAPI applications against temporary synthetic stores.

No Docker, AWS model calls, real customer data, or business mutations required.
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
BUSINESS={"sales":"lsk-sales-account","marketing":"lsk-marketing","finance":"lsk-finance"}

def pick_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]

def call(url,headers=None,body=None):
    req=urllib.request.Request(
        url,method="POST" if body is not None else "GET",
        headers=headers or {},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=8) as response:
            return response.status,json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code,json.load(exc)

def await_start(url,proc):
    end=time.monotonic()+25
    while time.monotonic()<end:
        if proc.poll() is not None:
            raise RuntimeError("Service process terminated")
        try:
            if call(url+"/health")[0]==200:
                return
        except (urllib.error.URLError,TimeoutError,ValueError):
            pass
        time.sleep(.3)
    raise TimeoutError("Service did not become healthy: "+url)

def run():
    ports={name:pick_port() for name in (*BUSINESS,"gateway")}
    children=[]
    with tempfile.TemporaryDirectory(prefix="lsk-enterprise-smoke-") as temp:
        base_env=os.environ.copy()
        base_env.update({
            "LSK_STAGE":"poc","LSK_TENANT_ID":"lsk-synthetic",
            "LSK_ENABLE_DEMO_WRITES":"false","GATEWAY_API_KEY":"smoke-test-gateway",
            "DEMO_API_KEY":"smoke-test-upstream","BEDROCK_MODEL_ID":"",
            "OPENAI_API_KEY":"",
        })
        for name in BUSINESS:
            base_env[name.upper()+"_SERVICE_URL"]="http://127.0.0.1:"+str(ports[name])
        try:
            for name in (*BUSINESS,"gateway"):
                folder=ROOT if name=="gateway" else ROOT/"external"/BUSINESS[name]
                if not folder.is_dir():
                    raise RuntimeError("Business app missing: "+str(folder))
                env={**base_env,"APP_DOMAIN":name,
                     "APP_DB_PATH":str(Path(temp)/(name+".sqlite3"))}
                logfile=Path(temp)/(name+".log")
                log=open(logfile,"w",encoding="utf-8")
                command=[sys.executable,"-m","uvicorn",
                         "integrations.gateway:app" if name=="gateway" else "app.main:app",
                         "--host","127.0.0.1","--port",str(ports[name])]
                proc=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
                children.append((name,proc,log,logfile))
                await_start("http://127.0.0.1:"+str(ports[name]),proc)
            base="http://127.0.0.1:"+str(ports["gateway"])
            headers={"X-API-Key":"smoke-test-gateway","X-Actor":"employee"}
            result,apps=call(base+"/v1/apps",headers)
            assert result==200 and set(apps)==set(BUSINESS),(result,apps)
            result,data=call(base+"/v1/platform/ask",{
                **headers,"Content-Type":"application/json"},
                {"question":"Explain the invoice exception review process.",
                 "domain":"finance","use_model":False})
            assert result==200 and data["mode"]=="retrieval-only",(result,data)
            assert any(doc["id"]=="lsk-invoice-standards-v1"
                       for doc in data["evidence"]["sources"])
            result,_=call(base+"/v1/apps/finance/proposals",{
                **headers,"Content-Type":"application/json"},
                {"record_id":"inv-1002","text":"Review","reason":"synthetic"})
            assert result==410,result
            result,_=call(base+"/v1/apps/finance/proposals/p1/decision",{
                **headers,"X-Role":"reviewer","Content-Type":"application/json"},
                {"approve":True})
            assert result==403,result
            print("PASS: real four-service HTTP topology, ACL retrieval and blocked legacy changes")
        except Exception:
            for name,proc,log,path in children:
                log.flush()
                print("--- "+name+" logs ---\n"+path.read_text(encoding="utf-8")[-2200:],file=sys.stderr)
            raise
        finally:
            for name,proc,log,_ in reversed(children):
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                log.close()

if __name__=="__main__":
    run()
