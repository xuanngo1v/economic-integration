#!/usr/bin/env python3
"""
Workflow: Supplier Spend Analysis
====================================
Analyze where your money goes — top suppliers, spend trends, category breakdown.

This is READ-ONLY.

Usage:
  python workflows/supplier_spend.py             # Last 90 days
  python workflows/supplier_spend.py --days 180  # Last 6 months
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def main(days: int = 90):
    today = date.today()
    print(f"Supplier Spend Analysis — last {days} days")
    print(f"Period: {(today - timedelta(days=days)).isoformat()} to {today.isoformat()}")
    print("=" * 55)

    invoices = get_all("/invoices/booked", params={"pagesize": 200, "sort": "-date"})

    if not invoices:
        print("\nNo booked invoices found.")
        return

    # Filter to period and analyze
    cutoff = today - timedelta(days=days)
    supplier_spend = defaultdict(lambda: {"total": 0.0, "count": 0, "invoices": []})
    monthly = defaultdict(float)
    total = 0.0
    in_period = 0

    for inv in invoices:
        inv_date_str = inv.get("date", "")
        if not inv_date_str:
            continue
        try:
            inv_date = date.fromisoformat(inv_date_str)
        except ValueError:
            continue
        if inv_date < cutoff:
            continue

        in_period += 1
        amount = abs(inv.get("grossAmount", 0) or 0)
        supplier = (inv.get("recipient") or {}).get("name", "Unknown")
        month_key = inv_date.strftime("%Y-%m")

        total += amount
        monthly[month_key] += amount
        supplier_spend[supplier]["total"] += amount
        supplier_spend[supplier]["count"] += 1
        supplier_spend[supplier]["invoices"].append({
            "number": inv.get("bookedInvoiceNumber"),
            "date": inv_date_str,
            "amount": amount,
        })

    print(f"\n  Invoices in period: {in_period}")
    print(f"  Total spend:       {total:>12,.0f}")
    if days >= 30:
        print(f"  Monthly average:   {total / (days / 30):>12,.0f}")

    # Top suppliers
    print("\n── Top Suppliers ────────────────────────────────")
    sorted_suppliers = sorted(supplier_spend.items(), key=lambda x: x[1]["total"], reverse=True)
    for i, (name, info) in enumerate(sorted_suppliers[:15], 1):
        pct = (info["total"] / total * 100) if total else 0
        print(f"  {i:>2}. {name:<35} {info['total']:>10,.0f}  ({info['count']} inv, {pct:.0f}%)")

    # Monthly trend
    if monthly:
        print("\n── Monthly Trend ────────────────────────────────")
        for month in sorted(monthly.keys()):
            bar_len = int(monthly[month] / max(monthly.values()) * 30) if max(monthly.values()) else 0
            bar = "█" * bar_len
            print(f"  {month}  {monthly[month]:>10,.0f}  {bar}")

    # Concentration warning
    if sorted_suppliers:
        top3_total = sum(s[1]["total"] for s in sorted_suppliers[:3])
        top3_pct = (top3_total / total * 100) if total else 0
        print(f"\n── Insights ─────────────────────────────────────")
        print(f"  Top 3 suppliers account for {top3_pct:.0f}% of total spend.")
        if top3_pct > 70:
            print("  That's quite concentrated — worth checking if you have alternatives.")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"supplier_spend_{today.isoformat()}.json"
    report = {
        "date": today.isoformat(),
        "period_days": days,
        "total_spend": total,
        "invoice_count": in_period,
        "suppliers": {k: {"total": v["total"], "count": v["count"]} for k, v in sorted_suppliers},
        "monthly": dict(monthly),
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supplier spend analysis")
    parser.add_argument("--days", type=int, default=90, help="Days to analyze (default: 90)")
    args = parser.parse_args()
    main(days=args.days)
