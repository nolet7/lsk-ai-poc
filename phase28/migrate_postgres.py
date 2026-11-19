"""Controlled migrations: run as a one-shot private task, not each API worker."""
from pathlib import Path
from phase28.production_app import database_connect

SQL = Path(__file__).resolve().parent / "sql"

def main():
    with database_connect() as db:
        db.execute("SELECT pg_advisory_lock(20280028)")
        try:
            for file in (SQL/"001_init_postgres.sql",SQL/"002_procurement.sql"):
                db.execute(file.read_text(encoding="utf-8"))
        finally:
            db.execute("SELECT pg_advisory_unlock(20280028)")
    print("Synthetic business schema migrations completed; no records seeded.")

if __name__ == "__main__":
    main()
