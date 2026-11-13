"""Persistent synthetic CRM and approval queue (SQLite, for local demonstration)."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("SALES_DB_PATH", "data/sales_demo.sqlite3"))
_lock = threading.RLock()
SEED_ACCOUNTS = [
    ("acme", "Acme Analytics", "Renewal", 120000, "2026-12-15", "Champion requested security FAQ; pricing review scheduled."),
    ("northstar", "Northstar Media", "Discovery", 85000, "2027-01-20", "Marketing lead wants a campaign performance demo."),
    ("orbit", "Orbit Commerce", "Negotiation", 210000, "2026-12-01", "Procurement requested revised commercial terms."),
]

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(str(DB_PATH), timeout=10)
    cx.row_factory = sqlite3.Row
    return cx

def initialize():
    with _lock, connect() as cx:
        cx.execute("CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, name TEXT, stage TEXT, amount INTEGER, close_date TEXT, notes TEXT)")
        cx.execute("CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, account_id TEXT NOT NULL, proposed_note TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL, requester TEXT NOT NULL, reviewer TEXT, created_at TEXT NOT NULL, reviewed_at TEXT)")
        cx.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, actor TEXT NOT NULL, event TEXT NOT NULL, reference_id TEXT NOT NULL, created_at TEXT NOT NULL, metadata TEXT NOT NULL)")
        if cx.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
            cx.executemany("INSERT INTO accounts VALUES(?,?,?,?,?,?)", SEED_ACCOUNTS)

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def audit(cx, actor, event, reference, metadata=None):
    cx.execute("INSERT INTO events VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()),actor,event,reference,utcnow(),json.dumps(metadata or {})))

def list_accounts():
    with connect() as cx:
        return [dict(r) for r in cx.execute("SELECT * FROM accounts ORDER BY name")]

def get_account(account_id):
    with connect() as cx:
        row=cx.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return dict(row) if row else None

def request_change(account_id, proposed_note, reason, requester):
    with _lock, connect() as cx:
        if not cx.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise KeyError("Account not found")
        approval_id=str(uuid.uuid4())
        cx.execute("INSERT INTO approvals (id,account_id,proposed_note,reason,status,requester,created_at) VALUES(?,?,?,?,?,?,?)",
                   (approval_id,account_id,proposed_note,reason,"pending",requester,utcnow()))
        audit(cx,requester,"approval_requested",approval_id,{"account_id":account_id})
        return get_approval_in_tx(cx,approval_id)

def get_approval_in_tx(cx, approval_id):
    row=cx.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
    return dict(row) if row else None

def get_approval(approval_id):
    with connect() as cx:
        return get_approval_in_tx(cx,approval_id)

def list_approvals():
    with connect() as cx:
        return [dict(r) for r in cx.execute("SELECT * FROM approvals ORDER BY created_at DESC")]

def decide(approval_id, reviewer, approve):
    with _lock, connect() as cx:
        current=get_approval_in_tx(cx,approval_id)
        if not current:
            raise KeyError("Approval not found")
        if current["status"]!="pending":
            raise ValueError("Approval was already decided")
        if current["requester"]==reviewer:
            raise PermissionError("Requester cannot approve their own change")
        new_status="approved" if approve else "rejected"
        cx.execute("UPDATE approvals SET status=?, reviewer=?, reviewed_at=? WHERE id=? AND status='pending'",
                   (new_status,reviewer,utcnow(),approval_id))
        if approve:
            account=cx.execute("SELECT notes FROM accounts WHERE id=?", (current["account_id"],)).fetchone()
            if not account:
                raise KeyError("Account no longer exists")
            new_notes=account["notes"]+"\n"+current["proposed_note"]
            cx.execute("UPDATE accounts SET notes=? WHERE id=?", (new_notes,current["account_id"]))
        audit(cx,reviewer,"approval_"+new_status,approval_id,{"account_id":current["account_id"]})
        return get_approval_in_tx(cx,approval_id)

def list_events():
    with connect() as cx:
        return [dict(r) for r in cx.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT 200")]
