#!/usr/bin/env python3
"""
Workflow: Cash Flow Check
===========================
Cash flow overview: money coming in (unpaid customer invoices)
vs money going out (supplier invoices due).

Shows both sides and the net position.

This is READ-ONLY.

Usage:
  python workflows/cashflow_check.py
"""

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import get_all, DATA_DIR


def _bucket_by_due_date(invoices, today):
    """Group invoices into time buckets based on due date."""
    by_period = defaultdict(float)
    overdue = 0.0
    total = 0.0

    for inv in invoices:
        amount = abs(inv.get("remainder", 0) or inv.get("grossAmount", 0) or 0)
        total += amount
        due_str = inv.get("dueDate", "")
        try:
            due = date.fromisoformat(due_str)
            if due < today:
                overdue += amount
            else:
                weeks_until = (due - today).days // 7
                if weeks_until <= 0:
                    by_period["This week"] += amount
                elif weeks_until <= 1:
                    by_period["Next week"] += amount
                elif weeks_until <= 4:
                    by_period["This month"] += amount
                else:
                    by_period["Later"] += amount
        except (ValueError, TypeError):
            by_period["Unknown"] += amount

    return total, overdue, by_period


def main():
    today = date.today()
    print(f"Cash Flow Check — {today.isoformat()}")
    print("=" * 55)

    # ── INCOMING: unpaid customer invoices ──
    print("\n── Money Coming In (Unpaid Invoices) ────────────")
    unpaid = get_all("/invoices/unpaid", params={"pagesize": 200})

    incoming_total, incoming_overdue, incoming_by_period = _bucket_by_due_date(unpaid, today)

    print(f"  Total expected:    {incoming_total:>12,.0f}")
    if incoming_overdue:
        print(f"  Already overdue:   {incoming_overdue:>12,.0f}  (should have been paid)")
    for period in ["This week", "Next week", "This month", "Later", "Unknown"]:
        if period in incoming_by_period:
            print(f"  Due {period:<15} {incoming_by_period[period]:>12,.0f}")

    # ── OUTGOING: supplier invoices (booked, recent) ──
    print("\n── Money Going Out (Supplier Bills) ─────────────")

    # Fetch recent booked invoices to estimate outgoing
    # e-conomic doesn't have a direct "unpaid supplier invoices" endpoint,
    # so we look at recent booked invoices and their payment status
    since_30d = (today.replace(day=1)).isoformat()  # Start of current month
    booked = get_all("/invoices/booked", params={
        "pagesize": 200,
        "filter": f"date$gte${since_30d}",
        "sort": "-date",
    })

    # Also check entries for supplier-type transactions
    entries = get_all("/entries", params={
        "pagesize": 500,
        "filter": f"date$gte${since_30d}",
    })

    # Estimate outgoing from supplier entries (negative amounts on COGS/expense accounts)
    outgoing_total = 0.0
    outgoing_by_supplier = defaultdict(float)
    for e in entries:
        amount = e.get("amount", 0) or 0
        acct = e.get("account") or {}
        num = acct.get("accountNumber") if isinstance(acct, dict) else None
        text = e.get("text", "")

        # Supplier-related entries are typically on COGS, premises, admin accounts
        if num and 2100 <= num <= 6999 and amount < 0:
            outgoing_total += abs(amount)
            supplier_name = text.split(" - ")[0] if " - " in text else (text[:30] if text else "Unknown")
            outgoing_by_supplier[supplier_name] += abs(amount)

    print(f"  Recent outgoing (this month): {outgoing_total:>12,.0f}")
    if outgoing_by_supplier:
        top_outgoing = sorted(outgoing_by_supplier.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  Top outgoing:")
        for name, amount in top_outgoing:
            print(f"    {name:<35} {amount:>10,.0f}")

    # ── NET POSITION ──
    print(f"\n── Net Cash Position ────────────────────────────")
    print(f"  Expected incoming: {incoming_total:>12,.0f}")
    print(f"  Recent outgoing:  -{outgoing_total:>12,.0f}")
    print(f"                     {'─' * 16}")
    net = incoming_total - outgoing_total
    print(f"  Net position:      {net:>12,.0f}")

    near_term_in = incoming_by_period.get("This week", 0) + incoming_by_period.get("Next week", 0) + incoming_overdue
    print(f"\n  Due in within 2 weeks: {near_term_in:>9,.0f}")

    # ── SUGGESTIONS ──
    print(f"\n── Suggestions ──────────────────────────────────")
    if incoming_overdue > 0:
        pct = (incoming_overdue / incoming_total * 100) if incoming_total else 0
        print(f"  {pct:.0f}% of outstanding invoices are overdue.")
        print(f"  Run: python workflows/overdue_invoices.py  for details.")
    if outgoing_total > incoming_total:
        print(f"  Outgoing exceeds expected incoming — monitor cash reserves.")
    if not unpaid:
        print("  No unpaid invoices — either all paid or no invoices sent yet.")
    if net > 0 and not incoming_overdue:
        print("  Cash position looks healthy.")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"cashflow_{today.isoformat()}.json"
    report = {
        "date": today.isoformat(),
        "incoming_total": incoming_total,
        "incoming_overdue": incoming_overdue,
        "incoming_by_period": dict(incoming_by_period),
        "outgoing_total": outgoing_total,
        "net_position": net,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved: {report_path}")

    # Log
    try:
        from log import log_action
        log_action("workflow", f"Cash flow check: incoming {incoming_total:,.0f}, outgoing {outgoing_total:,.0f}, net {net:,.0f}",
                   details=report)
    except Exception:
        pass


if __name__ == "__main__":
    main()
