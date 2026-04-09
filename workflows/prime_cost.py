#!/usr/bin/env python3
"""
Workflow: Prime Cost Analysis
================================
Calculates the prime cost ratio: (COGS + Labor) / Revenue.

This is one of the most important metrics for businesses with significant
cost of goods and labor. Industry benchmark: prime cost should be below 65% of revenue.

This is READ-ONLY.

Usage:
  python workflows/prime_cost.py
  python workflows/prime_cost.py --months 3
  python workflows/prime_cost.py --days 180
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import get_all, DATA_DIR

from account_map import map_account_category, CATEGORY_LABELS


def main(days: int = 30):
    today = date.today()
    since = (today - timedelta(days=days)).isoformat()

    print(f"Prime Cost Analysis — {today.isoformat()}")
    print(f"Period: last {days} days (since {since})")
    print("=" * 55)

    # Fetch entries
    entries = get_all("/entries", params={
        "pagesize": 1000,
        "filter": f"date$gte${since}",
    })

    if not entries:
        print("\n  No journal entries found for this period.")
        print("  Run: python run.py  to fetch data first.")
        return

    # Categorize
    totals = defaultdict(float)
    for e in entries:
        acct = e.get("account") or {}
        num = acct.get("accountNumber") if isinstance(acct, dict) else None
        cat = map_account_category(num)
        totals[cat] += e.get("amount", 0) or 0

    revenue = abs(totals.get("revenue", 0))
    cogs = abs(totals.get("cogs", 0))
    labor = abs(totals.get("labor", 0))
    prime_cost = cogs + labor

    if not revenue:
        print("\n  No revenue found in this period. Cannot calculate prime cost.")
        return

    prime_pct = (prime_cost / revenue) * 100
    cogs_pct = (cogs / revenue) * 100
    labor_pct = (labor / revenue) * 100

    # Display
    print(f"\n── Prime Cost Breakdown ─────────────────────────")
    print(f"  Revenue:              {revenue:>12,.0f}")
    print(f"  Cost of goods (COGS): {cogs:>12,.0f}  ({cogs_pct:.1f}%)")
    print(f"  Staff costs (Labor):  {labor:>12,.0f}  ({labor_pct:.1f}%)")
    print(f"                        {'─' * 16}")
    print(f"  Prime Cost:           {prime_cost:>12,.0f}  ({prime_pct:.1f}%)")

    # Benchmark
    print(f"\n── Assessment ───────────────────────────────────")
    if prime_pct <= 55:
        print(f"  Prime cost is {prime_pct:.1f}% — Excellent.")
        print(f"  Well below the 65% benchmark.")
    elif prime_pct <= 65:
        print(f"  Prime cost is {prime_pct:.1f}% — Healthy.")
        print(f"  Within the industry benchmark of 65%.")
    elif prime_pct <= 70:
        print(f"  Prime cost is {prime_pct:.1f}% — Elevated.")
        print(f"  Above the 65% benchmark. Review COGS or labor costs.")
    else:
        print(f"  Prime cost is {prime_pct:.1f}% — High.")
        print(f"  Significantly above the 65% benchmark.")
        if cogs_pct > labor_pct:
            print(f"  COGS ({cogs_pct:.1f}%) is the larger component — review supplier costs.")
        else:
            print(f"  Labor ({labor_pct:.1f}%) is the larger component — review staffing levels.")

    # Monthly breakdown if enough data
    if days >= 60:
        print(f"\n── Monthly Trend ────────────────────────────────")
        monthly = defaultdict(lambda: {"revenue": 0.0, "cogs": 0.0, "labor": 0.0})
        for e in entries:
            entry_date = e.get("date", "")[:7]  # YYYY-MM
            if not entry_date:
                continue
            acct = e.get("account") or {}
            num = acct.get("accountNumber") if isinstance(acct, dict) else None
            cat = map_account_category(num)
            if cat in ("revenue", "cogs", "labor"):
                monthly[entry_date][cat] += abs(e.get("amount", 0) or 0)

        print(f"  {'Month':<10} {'Revenue':>10} {'COGS':>10} {'Labor':>10} {'Prime':>10} {'%':>6}")
        print(f"  {'─' * 56}")
        for month in sorted(monthly.keys()):
            m = monthly[month]
            rev = m["revenue"]
            pc = m["cogs"] + m["labor"]
            pct = (pc / rev * 100) if rev else 0
            print(f"  {month:<10} {rev:>10,.0f} {m['cogs']:>10,.0f} {m['labor']:>10,.0f} {pc:>10,.0f} {pct:>5.1f}%")

    # Save report
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "date": today.isoformat(),
        "period_days": days,
        "revenue": revenue,
        "cogs": cogs,
        "labor": labor,
        "prime_cost": prime_cost,
        "prime_cost_pct": round(prime_pct, 1),
        "cogs_pct": round(cogs_pct, 1),
        "labor_pct": round(labor_pct, 1),
    }
    path = DATA_DIR / f"prime_cost_{today.isoformat()}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved: {path}")

    # Log
    try:
        from log import log_action
        log_action("workflow", f"Prime cost analysis: {prime_pct:.1f}% (COGS {cogs_pct:.1f}% + Labor {labor_pct:.1f}%)",
                   details=report)
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prime cost analysis")
    parser.add_argument("--months", type=int, default=None, help="Months to analyze (default: 1)")
    parser.add_argument("--days", type=int, default=None, help="Days to analyze")
    args = parser.parse_args()

    if args.days:
        main(days=args.days)
    elif args.months:
        main(days=args.months * 30)
    else:
        main(days=30)
