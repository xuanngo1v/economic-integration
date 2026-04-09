#!/usr/bin/env python3
"""
Ingest e-conomic Financial Data into SQLite
=============================================
Reads JSON files produced by fetch.py and inserts them into three tables:
supplier_invoices, financial_entries, accounts_chart.

After ingestion, prints a P&L summary from the database.

Usage:
  python ingest.py
  python ingest.py --date 2026-03-26
  python ingest.py --dry-run
"""

import argparse
import glob
import json
import sqlite3
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "economic_data.db"


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

CREATE_SUPPLIER_INVOICES = """
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT,
    supplier_name   TEXT,
    supplier_number INTEGER,
    date            TEXT NOT NULL,
    due_date        TEXT,
    amount          REAL NOT NULL,
    currency        TEXT,
    status          TEXT,
    account_number  INTEGER,
    category        TEXT,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    UNIQUE(invoice_number)
)
"""

CREATE_FINANCIAL_ENTRIES = """
CREATE TABLE IF NOT EXISTS financial_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    account_number  INTEGER NOT NULL,
    account_name    TEXT,
    amount          REAL NOT NULL,
    text            TEXT,
    entry_type      TEXT,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
)
"""

CREATE_ACCOUNTS_CHART = """
CREATE TABLE IF NOT EXISTS accounts_chart (
    account_number  INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    account_type    TEXT,
    category        TEXT
)
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_SUPPLIER_INVOICES)
    conn.execute(CREATE_FINANCIAL_ENTRIES)
    conn.execute(CREATE_ACCOUNTS_CHART)
    conn.commit()
    print("  [schema] Tables ready")


from account_map import map_account_category


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def latest_file(pattern: str) -> Path | None:
    matches = sorted(glob.glob(str(DATA_DIR / pattern)), reverse=True)
    return Path(matches[0]) if matches else None


def find_economic_files(target_date: str | None) -> dict[str, Path | None]:
    if target_date:
        return {
            "invoices": DATA_DIR / f"economic_invoices_{target_date}.json",
            "suppliers": DATA_DIR / f"economic_suppliers_{target_date}.json",
            "entries": DATA_DIR / f"economic_entries_{target_date}.json",
            "accounts": DATA_DIR / f"economic_accounts_{target_date}.json",
        }
    return {
        "invoices": latest_file("economic_invoices_*.json"),
        "suppliers": latest_file("economic_suppliers_*.json"),
        "entries": latest_file("economic_entries_*.json"),
        "accounts": latest_file("economic_accounts_*.json"),
    }


# ---------------------------------------------------------------------------
# Ingest functions
# ---------------------------------------------------------------------------

def ingest_accounts(conn: sqlite3.Connection, path: Path, dry_run: bool) -> int:
    if not path or not path.exists():
        print(f"  [skip] accounts file not found: {path}")
        return 0
    accounts = json.loads(path.read_text())
    count = 0
    for a in accounts:
        num = a.get("account_number")
        if num is None:
            continue
        if not dry_run:
            conn.execute("""
                INSERT OR REPLACE INTO accounts_chart (account_number, name, account_type, category)
                VALUES (?, ?, ?, ?)
            """, (num, a.get("name", ""), a.get("account_type", ""), map_account_category(num)))
        count += 1
    if not dry_run:
        conn.commit()
    print(f"  [accounts] {'(dry) ' if dry_run else ''}{count} rows -> accounts_chart")
    return count


def ingest_invoices(conn: sqlite3.Connection, path: Path, dry_run: bool) -> int:
    if not path or not path.exists():
        print(f"  [skip] invoices file not found: {path}")
        return 0
    invoices = json.loads(path.read_text())
    count = 0
    skipped = 0
    for inv in invoices:
        inv_date = inv.get("date", "")
        if not inv_date:
            skipped += 1
            continue
        if not dry_run:
            conn.execute("""
                INSERT OR IGNORE INTO supplier_invoices
                    (invoice_number, supplier_name, supplier_number, date, due_date,
                     amount, currency, status, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv.get("invoice_number"),
                inv.get("supplier_name", ""),
                inv.get("supplier_number"),
                inv_date,
                inv.get("due_date"),
                inv.get("amount", 0) or 0,
                inv.get("currency"),
                inv.get("status", "booked"),
                map_account_category(inv.get("account_number")),
            ))
        count += 1
    if not dry_run:
        conn.commit()
    print(f"  [invoices] {'(dry) ' if dry_run else ''}{count} inserted, {skipped} skipped")
    return count


def ingest_entries(conn: sqlite3.Connection, path: Path, dry_run: bool) -> int:
    if not path or not path.exists():
        print(f"  [skip] entries file not found: {path}")
        return 0
    entries = json.loads(path.read_text())
    count = 0
    skipped = 0
    for e in entries:
        e_date = e.get("date", "")
        acct_num = e.get("account_number")
        if not e_date or acct_num is None:
            skipped += 1
            continue
        if not dry_run:
            conn.execute("""
                INSERT INTO financial_entries
                    (date, account_number, account_name, amount, text, entry_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                e_date,
                acct_num,
                e.get("account_name", ""),
                e.get("amount", 0) or 0,
                e.get("text", ""),
                map_account_category(acct_num),
            ))
        count += 1
    if not dry_run:
        conn.commit()
    print(f"  [entries] {'(dry) ' if dry_run else ''}{count} inserted, {skipped} skipped")
    return count


# ---------------------------------------------------------------------------
# P&L report
# ---------------------------------------------------------------------------

def print_pl_report(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT entry_type, SUM(amount) as total
        FROM financial_entries
        GROUP BY entry_type
    """).fetchall()

    totals = {r["entry_type"]: r["total"] or 0 for r in rows}

    revenue = abs(totals.get("revenue", 0))
    cogs = abs(totals.get("cogs", 0))
    labor = abs(totals.get("labor", 0))
    premises = abs(totals.get("premises", 0))
    platform_fees = abs(totals.get("platform_fees", 0))
    admin = abs(totals.get("admin", 0))
    opex = premises + platform_fees + admin
    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue else 0
    net_profit = gross_profit - labor - opex

    print("\n── P&L from database ────────────────────────────")
    print(f"  Revenue:       {revenue:>12,.0f}")
    print(f"  COGS:          {cogs:>12,.0f}")
    print(f"  Gross Profit:  {gross_profit:>12,.0f}  ({gross_margin:.1f}%)")
    print(f"  Labor:         {labor:>12,.0f}")
    print(f"  OpEx:          {opex:>12,.0f}")
    print(f"  Net Profit:    {net_profit:>12,.0f}")

    rows2 = conn.execute("SELECT COUNT(*) as cnt, SUM(amount) as total FROM supplier_invoices").fetchone()
    if rows2 and rows2["cnt"]:
        print(f"\n── Supplier Invoices ─────────────────────────────")
        print(f"  Total invoices: {rows2['cnt']}")
        print(f"  Total spend:    {abs(rows2['total'] or 0):>12,.0f}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(target_date: str | None = None, dry_run: bool = False) -> None:
    today = date.today().isoformat()
    label = target_date or "latest"
    print(f"ingest — {today} (source: {label}){' [DRY RUN]' if dry_run else ''}")

    files = find_economic_files(target_date)
    missing = [k for k, v in files.items() if not v or not v.exists()]
    if missing:
        print(f"  [warn] Missing files: {missing}")
        if len(missing) == len(files):
            print("  No data files found. Run fetch.py first.")
            return

    conn = get_conn()
    ensure_tables(conn)

    ingest_accounts(conn, files["accounts"], dry_run)
    ingest_invoices(conn, files["invoices"], dry_run)
    ingest_entries(conn, files["entries"], dry_run)

    if not dry_run:
        print_pl_report(conn)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest e-conomic JSON into SQLite")
    parser.add_argument("--date", dest="target_date", default=None,
                        help="Use files for specific date (YYYY-MM-DD). Default: latest.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and count without inserting into DB")
    args = parser.parse_args()
    main(target_date=args.target_date, dry_run=args.dry_run)
