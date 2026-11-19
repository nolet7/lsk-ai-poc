"""Approved one-shot schema migration and restricted application-role provisioning.

Dedicated migration task receives RDS master credentials. API/MCP tasks must not.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from psycopg import sql
from phase28.production_app import database_connect

SCHEMA = Path(__file__).resolve().parent / "sql"


def main():
    user = os.environ["LSK_APP_DB_USERNAME"]
    password = os.environ["LSK_APP_DB_PASSWORD"]
    if not re.fullmatch(r"[a-z_][a-z0-9_]{2,30}", user):
        raise RuntimeError("Invalid application DB role name")
    if not isinstance(password, str) or len(password) < 24:
        raise RuntimeError("Application DB password must be at least 24 characters")
    with database_connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(20280028)")
        for file in (SCHEMA / "001_init_postgres.sql", SCHEMA / "002_procurement.sql", SCHEMA / "003_procurement_knowledge.sql"):
            db.execute(file.read_text(encoding="utf-8"))
        role = sql.Identifier(user)
        if db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (user,)).fetchone() is None:
            db.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                role, sql.Literal(password)))
        else:
            db.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                role, sql.Literal(password)))
        db.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(db.info.dbname), role))
        db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        db.execute(sql.SQL(
            "GRANT SELECT ON TABLE sources, procurement_pos, procurement_invoices, "
            "procurement_certificates, procurement_knowledge TO {}").format(role))
        db.execute(sql.SQL(
            "GRANT SELECT, INSERT ON TABLE audit, model_attempts, procurement_exceptions TO {}").format(role))
        db.execute(sql.SQL(
            "GRANT UPDATE (status, reviewer, reviewed_at) ON TABLE procurement_exceptions TO {}").format(role))
    print("Schema and restricted application role prepared. No customer data seeded.")


if __name__ == "__main__":
    main()
