#!/usr/bin/env python3
"""
Workflow: Profit & Loss Report
================================
Generates a P&L from your journal entries, adapting to YOUR chart of accounts.

Instead of assuming account ranges, it reads your actual chart of accounts first
and groups by what your accountant set up.

This is READ-ONLY.

Usage:
  python workflows/pl_report.py              # Last 30 days
  python workflows/pl_report.py --months 3   # Last 3 months
  python workflows/pl_report.py --months 12  # Full year
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
from account_map import map_account_category as categorize, CATEGORY_LABELS, PL_ORDER


def main(months: int = 1):
    today = date.today()
    since = (today - timedelta(days=months * 30)).isoformat()

    print(f"Profit & Loss Report — last {months} month(s)")
    print(f"Period: {since} to {today.isoformat()}")
    print("=" * 55)

    # Fetch entries (try direct, then fallback to accounting years)
    entries = get_all("/entries", params={
        "pagesize": 1000,
        "filter": f"date$gte${since}",
    })

    if not entries:
        # Fallback: fetch via accounting years
        since_date = today - timedelta(days=months * 30)
        years = set()
        d = since_date
        while d <= today:
            years.add(d.year)
            d = date(d.year + 1, 1, 1)
        print(f"  Fetching via accounting years: {sorted(years)}...")
        for year in sorted(years):
            year_items = get_all(f"/accounting-years/{year}/entries", params={"pagesize": 1000})
            entries.extend(e for e in year_items if e.get("date", "") >= since)

    if not entries:
        print("\nNo journal entries found for this period.")
        return

    print(f"\nAnalyzing {len(entries)} journal entries...\n")

    # Group by category and account
    by_category = defaultdict(lambda: {"total": 0.0, "accounts": defaultdict(lambda: {"name": "", "total": 0.0})})

    for e in entries:
        acct = e.get("account") or {}
        num = acct.get("accountNumber") if isinstance(acct, dict) else None
        name = acct.get("name", "") if isinstance(acct, dict) else ""
        amount = e.get("amount", 0) or 0
        cat = categorize(num)

        by_category[cat]["total"] += amount
        if num is not None:
            by_category[cat]["accounts"][num]["name"] = name
            by_category[cat]["accounts"][num]["total"] += amount

    # Calculate P&L lines
    revenue = abs(by_category["revenue"]["total"])
    cogs = abs(by_category["cogs"]["total"])
    labor = abs(by_category["labor"]["total"])
    premises = abs(by_category["premises"]["total"])
    transport = abs(by_category["transport"]["total"])
    platform_fees = abs(by_category["platform_fees"]["total"])
    admin = abs(by_category["admin"]["total"])
    other_ops = abs(by_category["other_ops"]["total"])
    depreciation = abs(by_category["depreciation"]["total"])
    fin_income = abs(by_category["financial_income"]["total"])
    fin_expense = abs(by_category["financial_expense"]["total"])

    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue else 0
    total_opex = premises + transport + platform_fees + admin + other_ops
    operating_profit = gross_profit - labor - total_opex - depreciation
    net_profit = operating_profit + fin_income - fin_expense

    # Print P&L
    print("── Profit & Loss (P&L) ─────────────────────────")
    print(f"  Revenue:                    {revenue:>12,.0f}")
    print(f"  Cost of goods (COGS):      -{cogs:>12,.0f}")
    print(f"                              {'─' * 16}")
    print(f"  Gross profit:               {gross_profit:>12,.0f}  ({gross_margin:.1f}%)")
    print()
    print(f"  Staff costs (labor):       -{labor:>12,.0f}")
    print(f"  Premises:                  -{premises:>12,.0f}")
    if transport:
        print(f"  Transport:                 -{transport:>12,.0f}")
    print(f"  Platform fees:             -{platform_fees:>12,.0f}")
    print(f"  Administration:            -{admin:>12,.0f}")
    if other_ops:
        print(f"  Other operating:           -{other_ops:>12,.0f}")
    if depreciation:
        print(f"  Depreciation:              -{depreciation:>12,.0f}")
    print(f"                              {'─' * 16}")
    print(f"  Operating profit:           {operating_profit:>12,.0f}")
    print()
    if fin_income:
        print(f"  Financial income:          +{fin_income:>12,.0f}")
    if fin_expense:
        print(f"  Financial expense:         -{fin_expense:>12,.0f}")
    print(f"                              {'─' * 16}")
    print(f"  Net profit (before tax):    {net_profit:>12,.0f}")

    # Key ratios
    if revenue:
        print("\n── Key Ratios ───────────────────────────────────")
        print(f"  Gross margin:        {gross_margin:>6.1f}%")
        print(f"  COGS ratio:          {(cogs/revenue*100):>6.1f}%")
        print(f"  Labor ratio:         {(labor/revenue*100):>6.1f}%")
        print(f"  Platform fee ratio:  {(platform_fees/revenue*100):>6.1f}%")
        print(f"  Net margin:          {(net_profit/revenue*100):>6.1f}%")

    # Top accounts in each category
    print("\n── Breakdown by Account ─────────────────────────")
    for cat in ["revenue", "cogs", "labor", "premises", "platform_fees", "admin"]:
        if cat in by_category and by_category[cat]["accounts"]:
            print(f"\n  {CATEGORY_LABELS.get(cat, cat)}:")
            sorted_accts = sorted(
                by_category[cat]["accounts"].items(),
                key=lambda x: abs(x[1]["total"]),
                reverse=True,
            )
            for num, info in sorted_accts[:5]:
                print(f"    {num:>6}  {info['name']:<40} {abs(info['total']):>10,.0f}")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"pl_report_{today.isoformat()}.json"
    report = {
        "date": today.isoformat(),
        "period_from": since,
        "period_to": today.isoformat(),
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_pct": round(gross_margin, 1),
        "labor": labor,
        "premises": premises,
        "transport": transport,
        "platform_fees": platform_fees,
        "admin": admin,
        "depreciation": depreciation,
        "operating_profit": operating_profit,
        "financial_income": fin_income,
        "financial_expense": fin_expense,
        "net_profit": net_profit,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P&L report from e-conomic")
    parser.add_argument("--months", type=int, default=1, help="How many months back (default: 1)")
    args = parser.parse_args()
    main(months=args.months)
