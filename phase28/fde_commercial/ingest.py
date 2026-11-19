"""Operator-controlled ingestion of approved SYNTHETIC document manifests.

This is not a live S3 ingestion pipeline. It requires reviewed input and DB access
granted to an ingestion administrator, not the API role.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from phase28.production_app import database_connect

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ALLOWED_ROLES = frozenset(("procurement","procurement_reviewer"))
ALLOWED_TYPES = frozenset(("contract","certificate","policy"))
URI = re.compile(r"^urn:lsk:synthetic:[A-Za-z0-9._:-]+$")

def validate_record(doc: dict) -> dict:
    if not isinstance(doc,dict) or set(doc)!={
        "tenant_id","source_id","po_id","doc_type","source_version",
        "source_uri","classification","authorized_roles","content"
    }:
        raise ValueError("Invalid document manifest")
    if any(not isinstance(doc[field],str) or not ID.fullmatch(doc[field]) 
           for field in ("tenant_id","source_id","po_id")):
        raise ValueError("Invalid document identity")
    if (doc["doc_type"] not in ALLOWED_TYPES or doc["classification"]!="synthetic"
            or not isinstance(doc["source_version"],int)
            or isinstance(doc["source_version"],bool) or doc["source_version"]<1):
        raise ValueError("Unapproved document type/version")
    roles=doc["authorized_roles"]
    if (not isinstance(roles,list) or not roles or len(roles)>2
            or not all(isinstance(r,str) and r in ALLOWED_ROLES for r in roles)
            or len(set(roles))!=len(roles)):
        raise ValueError("Invalid role ACL")
    if not isinstance(doc["source_uri"],str) or not URI.fullmatch(doc["source_uri"]):
        raise ValueError("Only synthetic provenance identifiers allowed")
    content=doc["content"]
    if not isinstance(content,str) or not 1<=len(content)<=5000:
        raise ValueError("Invalid document content")
    return {**doc,"authorized_roles":sorted(roles),
            "content_sha256":hashlib.sha256(content.encode("utf-8")).hexdigest()}

def ingest(docs: list[dict], connect=database_connect) -> int:
    if not isinstance(docs,list) or not 1<=len(docs)<=100:
        raise ValueError("Only bounded approved batches allowed")
    prepared=[validate_record(x) for x in docs]
    if len({(d["tenant_id"],d["source_id"]) for d in prepared})!=len(prepared):
        raise ValueError("Duplicate document identity")
    with connect() as db:
        for d in prepared:
            row=db.execute(
                """INSERT INTO procurement_knowledge
                   (tenant_id,source_id,po_id,doc_type,source_version,
                    source_uri,classification,authorized_roles,content,content_sha256,approved_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (tenant_id,source_id) DO NOTHING
                   RETURNING content_sha256""",
                (d["tenant_id"],d["source_id"],d["po_id"],d["doc_type"],
                 d["source_version"],d["source_uri"],d["classification"],
                 d["authorized_roles"],d["content"],d["content_sha256"],
                 datetime.now(timezone.utc))).fetchone()
            if row is None:
                existing=db.execute(
                    """SELECT po_id,doc_type,source_version,source_uri,classification,
                              authorized_roles,content_sha256 FROM procurement_knowledge
                       WHERE tenant_id=%s AND source_id=%s""",
                    (d["tenant_id"],d["source_id"])).fetchone()
                expected=(d["po_id"],d["doc_type"],d["source_version"],
                          d["source_uri"],d["classification"],d["authorized_roles"],
                          d["content_sha256"])
                if existing is None or tuple(existing)!=expected:
                    raise ValueError("Immutable document ID reused with changed content or ACL")
    return len(prepared)

def main() -> None:
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python -m phase28.fde_commercial.ingest reviewed-synthetic-documents.json")
    path=Path(sys.argv[1])
    docs=json.loads(path.read_text(encoding="utf-8"))
    count=ingest(docs)
    print(f"Validated {count} synthetic document records; no real customer data processed.")

if __name__=="__main__":
    main()
