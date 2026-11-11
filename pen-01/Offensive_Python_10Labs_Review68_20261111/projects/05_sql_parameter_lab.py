"""Illustrate unsafe SQL assembly versus bound parameters, offline only."""
import sqlite3
import sys
from contextlib import closing


def find_accounts(mode, name):
    if mode not in ("safe", "unsafe"):
        raise ValueError("mode must be safe or unsafe")
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE accounts (username TEXT NOT NULL)")
        db.executemany("INSERT INTO accounts VALUES (?)", [("alice",), ("bob",)])
        if mode == "safe":
            query = "SELECT username FROM accounts WHERE username = ?"
            rows = db.execute(query, (name,)).fetchall()
        else:
            # Intentionally unsafe: classroom example only, never reuse.
            query = f"SELECT username FROM accounts WHERE username = '{name}'"
            rows = db.execute(query).fetchall()
    return [row[0] for row in rows]


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("safe", "unsafe"):
        print("Usage: python3 05_sql_parameter_lab.py safe|unsafe username")
        return 2
    if len(sys.argv[2]) > 80:
        print("Error: username exceeds 80 characters")
        return 2
    try:
        results = find_accounts(sys.argv[1], sys.argv[2])
    except sqlite3.Error as exc:
        print(f"SQL rejected input: {exc}")
        return 1
    print("Matches:", ", ".join(results) if results else "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
