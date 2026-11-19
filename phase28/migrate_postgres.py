"""Run once via approved private migration task, never inside each application worker."""
from pathlib import Path
from phase28.production_app import database_connect

SCHEMA = Path(__file__).resolve().parent / "sql" / "001_init_postgres.sql"

def main():
    sql = SCHEMA.read_text(encoding="utf-8")
    with database_connect() as db:
        db.execute(sql)
    print("PostgreSQL schema migration applied; no customer records were loaded.")

if __name__ == "__main__":
    main()
