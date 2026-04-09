#!/usr/bin/env python3
"""
Workflow: Suggest Next Actions
================================
Analyzes the current state of your e-conomic data and suggests
relevant workflows to run. Adapts to YOUR setup.

This is READ-ONLY.

Usage:
  python workflows/suggest.py
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def _count(path, params=None):
    data = get(path, params={**(params or {}), "pagesize": 1})
    if data and "pagination" in data:
        return data["pagination"].get("results", 0)
    return 0


def main():
    today = date.today()
    print(f"Workflow Suggestions — {today.isoformat()}")
    print("Checking your e-conomic status...\n")

    suggestions = []
    checks = []

    # 1. Overdue invoices
    overdue_count = _count("/invoices/overdue")
    if overdue_count > 0:
        suggestions.append({
            "priority": "HIGH",
            "action": f"You have {overdue_count} overdue invoice(s). Someone owes you money.",
            "command": "python workflows/overdue_invoices.py",
            "why": "Overdue invoices mean cash you should have received but haven't. The longer you wait, the harder it gets to collect.",
        })
        checks.append(f"overdue_invoices: {overdue_count}")
    else:
        checks.append("overdue_invoices: 0 — all good")

    # 2. Unpaid invoices
    unpaid_count = _count("/invoices/unpaid")
    if unpaid_count > 5:
        suggestions.append({
            "priority": "MEDIUM",
            "action": f"You have {unpaid_count} unpaid invoices outstanding.",
            "command": "python workflows/cashflow_check.py",
            "why": "Good to know your cash flow position — how much is expected and when.",
        })
        checks.append(f"unpaid_invoices: {unpaid_count}")
    else:
        checks.append(f"unpaid_invoices: {unpaid_count}")

    # 3. Draft invoices sitting around
    draft_count = _count("/invoices/drafts")
    if draft_count > 0:
        suggestions.append({
            "priority": "MEDIUM",
            "action": f"You have {draft_count} draft invoice(s) not yet booked.",
            "command": None,
            "why": "Draft invoices are prepared but not finalized. Check if they should be booked and sent, or deleted.",
        })
        checks.append(f"draft_invoices: {draft_count}")
    else:
        checks.append("draft_invoices: 0")

    # 4. Recent activity check
    week_ago = (today - timedelta(days=7)).isoformat()
    recent = get("/entries", params={"pagesize": 1, "filter": f"date$gte${week_ago}"})
    recent_count = 0
    if recent and "pagination" in recent:
        recent_count = recent["pagination"].get("results", 0)
    if recent_count == 0:
        suggestions.append({
            "priority": "LOW",
            "action": "No journal entries in the last 7 days.",
            "command": "python workflows/pl_report.py --months 1",
            "why": "Could be normal (quiet week) or a sign that bookkeeping is falling behind. Run a P&L to see the current picture.",
        })
        checks.append("recent_entries_7d: 0 — quiet week")
    else:
        checks.append(f"recent_entries_7d: {recent_count}")

    # 5. Monthly P&L suggestion (always useful)
    last_pl = list(DATA_DIR.glob("pl_report_*.json")) if DATA_DIR.exists() else []
    if not last_pl:
        suggestions.append({
            "priority": "LOW",
            "action": "No P&L report generated yet. Good to have a baseline.",
            "command": "python workflows/pl_report.py --months 3",
            "why": "Understanding your revenue, costs, and margins is the foundation of financial health.",
        })

    # 6. Supplier review suggestion (monthly)
    last_supplier = list(DATA_DIR.glob("supplier_spend_*.json")) if DATA_DIR.exists() else []
    if not last_supplier:
        suggestions.append({
            "priority": "LOW",
            "action": "No supplier spend analysis done yet.",
            "command": "python workflows/supplier_spend.py --days 90",
            "why": "Knowing where your money goes helps you negotiate better deals and spot unusual charges.",
        })

    # 7. Explorer freshness
    last_explore = sorted(DATA_DIR.glob("explorer_report_*.json"), reverse=True) if DATA_DIR.exists() else []
    if not last_explore:
        suggestions.append({
            "priority": "HIGH",
            "action": "No explorer report found. Run explore.py first to map your setup.",
            "command": "python explore.py",
            "why": "The explorer maps your chart of accounts, journals, suppliers, and more. Everything else builds on this.",
        })
    else:
        explore_date = last_explore[0].stem.split("_")[-1]
        try:
            days_old = (today - date.fromisoformat(explore_date)).days
            if days_old > 30:
                suggestions.append({
                    "priority": "LOW",
                    "action": f"Explorer report is {days_old} days old. Things may have changed.",
                    "command": "python explore.py",
                    "why": "New accounts, suppliers, or products may have been added since the last scan.",
                })
        except ValueError:
            pass

    # Print results
    print("── Status Checks ────────────────────────────────")
    for c in checks:
        print(f"  {c}")

    if suggestions:
        print(f"\n── Suggestions ({len(suggestions)}) ─────────────────────────────")
        for s in sorted(suggestions, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["priority"], 3)):
            print(f"\n  [{s['priority']}] {s['action']}")
            print(f"  Why: {s['why']}")
            if s["command"]:
                print(f"  Run: {s['command']}")
    else:
        print("\n  Everything looks good. No urgent actions needed.")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {"date": today.isoformat(), "checks": checks, "suggestions": suggestions}
    path = DATA_DIR / f"suggestions_{today.isoformat()}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {path}")


if __name__ == "__main__":
    main()
