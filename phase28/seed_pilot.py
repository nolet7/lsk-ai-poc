"""Operator CLI for loading explicitly reviewed, non-sensitive pilot evidence."""
import argparse
import json
from pathlib import Path
import sqlite3

from phase28.authorization import DocumentScope
from phase28.live_app import initialize_database


def seed(db_path: Path, file_path: Path) -> int:
    if file_path.is_symlink() or file_path.stat().st_size > 100_000:
        raise ValueError("Untrusted pilot evidence file")
    rows = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not (1 <= len(rows) <= 50):
        raise ValueError("Expected 1-50 records")
    checked = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"source_id", "tenant_id", "domain", "record_id", "content"}:
            raise ValueError("Invalid record shape")
        DocumentScope(row["tenant_id"], row["domain"])
        if any(not isinstance(row[k], str) or not 1 <= len(row[k]) <= 128
               for k in ("source_id", "record_id")):
            raise ValueError("Invalid source identifier")
        if not isinstance(row["content"], str) or not 1 <= len(row["content"]) <= 1200:
            raise ValueError("Invalid evidence length")
        checked.append(tuple(row[k] for k in ("source_id", "tenant_id", "domain", "record_id", "content")))
    initialize_database(db_path)
    with sqlite3.connect(db_path) as con:
        con.executemany("INSERT INTO sources VALUES (?,?,?,?,?)", checked)
    return len(checked)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print(f"Inserted {seed(args.db, args.input)} pilot records")


if __name__ == "__main__":
    main()
