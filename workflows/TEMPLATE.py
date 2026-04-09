#!/usr/bin/env python3
"""
Workflow: [NAME]
==================
[One-line description of what this workflow does]

[Longer explanation: what question does it answer? who is it for?
 what data does it use?]

Type: [READ-ONLY / WRITE (needs approval)]

Usage:
  python workflows/[name].py
  python workflows/[name].py --option value
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# -- Setup (same for all workflows) ----------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def load_schema() -> dict:
    """Load schema.json for fast lookups. Returns empty dict if not found."""
    if SCHEMA_PATH.exists():
        return json.loads(SCHEMA_PATH.read_text())
    return {}


def save_report(name: str, data: dict) -> Path:
    """Save a report to data/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{name}_{date.today().isoformat()}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return path


# -- Your workflow logic goes here -----------------------------------------

def main():
    today = date.today()
    print(f"[Workflow Name] — {today.isoformat()}")
    print("=" * 55)

    # 1. Load schema for fast lookups (optional but recommended)
    schema = load_schema()

    # 2. Fetch the data you need from the API
    #    Examples:
    #    invoices = _get_all("/invoices/booked", params={"pagesize": 200})
    #    entries = _get_all("/entries", params={"pagesize": 1000, "filter": f"date$gte$2026-01-01"})
    #    suppliers = _get_all("/suppliers", params={"pagesize": 200})
    #    Or look things up from schema:
    #    account = schema.get("accounts", {}).get("lookup", {}).get("3010", {})

    # 3. Analyze

    # 4. Print results in plain language

    # 5. Save report
    #    report = {"date": today.isoformat(), "results": ...}
    #    path = save_report("workflow_name", report)
    #    print(f"\n  Report saved: {path}")

    # 6. Log the action (import from log.py)
    #    from log import log_action
    #    log_action("workflow", "Ran [workflow name]: [summary of findings]")

    print("\n  (This is a template — replace with your workflow logic)")


if __name__ == "__main__":
    # Add any CLI arguments your workflow needs
    parser = argparse.ArgumentParser(description="[Workflow description]")
    # parser.add_argument("--days", type=int, default=90, help="Days to analyze")
    # parser.add_argument("--brand", help="Filter by brand")
    args = parser.parse_args()
    main()
