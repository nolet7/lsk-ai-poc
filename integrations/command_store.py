"""Durable, idempotent *proposal-only* command boundary.

No ERP API writes and NO automatic approval. SQLite is appropriate only for the
local synthetic POC; production requires managed persistence and a workflow
engine plus verified human reviewer identity.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

def connect():
    path = Path(os.getenv("LSK_COMMAND_DB", "/tmp/lsk-demo-command.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(str(path), timeout=8)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA busy_timeout=8000")
    con.execute("""CREATE TABLE IF NOT EXISTS proposals(
        proposal_id TEXT PRIMARY KEY, tenant TEXT NOT NULL, actor TEXT NOT NULL,
        domain TEXT NOT NULL, record_id TEXT NOT NULL, payload TEXT NOT NULL,
        idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status='pending'), created_at INTEGER NOT NULL,
        UNIQUE(tenant, actor, idempotency_key))""")
    return con

def submit(*, tenant: str, actor: str, domain: str, record_id: str,
           text: str, reason: str, idempotency_key: str) -> dict:
    if not idempotency_key or len(idempotency_key)>128:
        raise ValueError("Valid Idempotency-Key required")
    content=json.dumps({"domain":domain,"record_id":record_id,"text":text,"reason":reason},
                       sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(content.encode()).hexdigest()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        existing=con.execute("SELECT * FROM proposals WHERE tenant=? AND actor=? AND idempotency_key=?",
                             (tenant,actor,idempotency_key)).fetchone()
        if existing:
            if existing["request_hash"]!=digest:
                raise ValueError("Idempotency-Key already used with a different payload")
            return {"proposal_id":existing["proposal_id"],"status":"pending","replayed":True}
        uid=str(uuid.uuid4())
        con.execute("INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (uid,tenant,actor,domain,record_id,content,idempotency_key,digest,"pending",int(time.time())))
        return {"proposal_id":uid,"status":"pending","replayed":False}

def my_proposals(tenant: str, actor: str) -> list[dict]:
    with connect() as con:
        rows=con.execute("SELECT proposal_id,domain,record_id,status,created_at FROM proposals WHERE tenant=? AND actor=? ORDER BY created_at DESC LIMIT 100",(tenant,actor)).fetchall()
        return [dict(row) for row in rows]
