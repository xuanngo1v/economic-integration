#!/usr/bin/env python3
"""
Workflow: Overdue Invoices
============================
Find all overdue invoices — who owes you money, how much, and how long.

Output: aging breakdown (0-30, 30-60, 60-90, 90+ days) and action suggestions.

This is READ-ONLY. Nothing is changed.

Usage:
  python workflows/overdue_invoices.py
"""

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def main():
    today = date.today()
    print(f"Overdue Invoices — {today.isoformat()}")
    print("=" * 50)

    # Fetch overdue invoices
    overdue = get_all("/invoices/overdue", params={"pagesize": 200, "sort": "-dueDate"})

    if not overdue:
        print("\nNo overdue invoices. You're all caught up!")
        return

    # Aging buckets
    buckets = {"0-30 days": [], "30-60 days": [], "60-90 days": [], "90+ days": []}
    total = 0.0
    by_customer = defaultdict(lambda: {"amount": 0.0, "count": 0, "oldest": ""})

    for inv in overdue:
        due_str = inv.get("dueDate", "")
        amount = abs(inv.get("remainder", 0) or inv.get("grossAmount", 0) or 0)
        customer_name = (inv.get("customer") or {}).get("name", (inv.get("recipient") or {}).get("name", "Unknown"))
        inv_number = inv.get("bookedInvoiceNumber", "?")

        total += amount

        try:
            due = date.fromisoformat(due_str)
            days_overdue = (today - due).days
        except (ValueError, TypeError):
            days_overdue = 0

        entry = {
            "invoice": inv_number,
            "customer": customer_name,
            "amount": amount,
            "due_date": due_str,
            "days_overdue": days_overdue,
        }

        if days_overdue <= 30:
            buckets["0-30 days"].append(entry)
        elif days_overdue <= 60:
            buckets["30-60 days"].append(entry)
        elif days_overdue <= 90:
            buckets["60-90 days"].append(entry)
        else:
            buckets["90+ days"].append(entry)

        by_customer[customer_name]["amount"] += amount
        by_customer[customer_name]["count"] += 1
        if not by_customer[customer_name]["oldest"] or due_str < by_customer[customer_name]["oldest"]:
            by_customer[customer_name]["oldest"] = due_str

    # Print summary
    print(f"\nTotal overdue: {total:,.0f} across {len(overdue)} invoices")

    print("\n── Aging Breakdown ──────────────────────────────")
    for bucket, entries in buckets.items():
        if entries:
            bucket_total = sum(e["amount"] for e in entries)
            print(f"\n  {bucket}: {len(entries)} invoices, {bucket_total:,.0f}")
            for e in entries[:5]:
                print(f"    Invoice #{e['invoice']}  {e['customer']:<30} {e['amount']:>10,.0f}  ({e['days_overdue']}d overdue)")
            if len(entries) > 5:
                print(f"    ... and {len(entries) - 5} more")

    print("\n── By Customer ──────────────────────────────────")
    sorted_customers = sorted(by_customer.items(), key=lambda x: x[1]["amount"], reverse=True)
    for name, info in sorted_customers[:10]:
        print(f"  {name:<35} {info['amount']:>10,.0f}  ({info['count']} invoices, oldest: {info['oldest']})")

    # Suggestions
    print("\n── Suggestions ──────────────────────────────────")
    if buckets["90+ days"]:
        print(f"  ! {len(buckets['90+ days'])} invoices are 90+ days overdue — consider sending reminders or escalating.")
    if buckets["60-90 days"]:
        print(f"  ! {len(buckets['60-90 days'])} invoices approaching 90 days — follow up soon.")
    if sorted_customers:
        top = sorted_customers[0]
        print(f"  Largest debtor: {top[0]} owes {top[1]['amount']:,.0f}.")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"overdue_report_{today.isoformat()}.json"
    report = {
        "date": today.isoformat(),
        "total_overdue": total,
        "invoice_count": len(overdue),
        "aging": {k: v for k, v in buckets.items()},
        "by_customer": dict(by_customer),
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
