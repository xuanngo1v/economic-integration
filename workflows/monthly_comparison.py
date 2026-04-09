#!/usr/bin/env python3
"""
Workflow: Monthly Comparison
===============================
Compare financial performance month-over-month.

Shows a table of Revenue, COGS, Labor, Gross Margin %, and Net Profit
for each month, with change indicators for significant swings.

This is READ-ONLY.

Usage:
  python workflows/monthly_comparison.py
  python workflows/monthly_comparison.py --months 6
  python workflows/monthly_comparison.py --months 12
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


def _change_indicator(current: float, previous: float) -> str:
    """Return a change indicator: +12%, -5%, or ~ for small changes."""
    if not previous:
        return ""
    pct = ((current - previous) / abs(previous)) * 100
    if abs(pct) < 3:
        return ""
    elif pct > 10:
        return f"  ++ {pct:+.0f}%"
    elif pct > 0:
        return f"  + {pct:+.0f}%"
    elif pct < -10:
        return f"  -- {pct:+.0f}%"
    else:
        return f"  {pct:+.0f}%"


def main(months: int = 3):
    today = date.today()
    days = months * 31  # slight overshoot to capture full months
    since = (today - timedelta(days=days)).isoformat()

    print(f"Monthly Comparison — {today.isoformat()}")
    print(f"Period: last {months} months")
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

    # Group by month and category
    monthly = defaultdict(lambda: defaultdict(float))
    for e in entries:
        entry_date = e.get("date", "")[:7]  # YYYY-MM
        if not entry_date:
            continue
        acct = e.get("account") or {}
        num = acct.get("accountNumber") if isinstance(acct, dict) else None
        cat = map_account_category(num)
        monthly[entry_date][cat] += e.get("amount", 0) or 0

    if not monthly:
        print("\n  No data to compare.")
        return

    sorted_months = sorted(monthly.keys())

    # Build summary per month
    summaries = []
    for month in sorted_months:
        m = monthly[month]
        revenue = abs(m.get("revenue", 0))
        cogs = abs(m.get("cogs", 0))
        labor = abs(m.get("labor", 0))
        premises = abs(m.get("premises", 0))
        platform_fees = abs(m.get("platform_fees", 0))
        admin = abs(m.get("admin", 0))
        other_ops = abs(m.get("other_ops", 0))
        depreciation = abs(m.get("depreciation", 0))
        fin_income = abs(m.get("financial_income", 0))
        fin_expense = abs(m.get("financial_expense", 0))

        total_opex = premises + platform_fees + admin + other_ops
        gross_profit = revenue - cogs
        gross_margin = (gross_profit / revenue * 100) if revenue else 0
        net_profit = gross_profit - labor - total_opex - depreciation + fin_income - fin_expense
        net_margin = (net_profit / revenue * 100) if revenue else 0
        prime_cost_pct = ((cogs + labor) / revenue * 100) if revenue else 0

        summaries.append({
            "month": month,
            "revenue": revenue,
            "cogs": cogs,
            "labor": labor,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
            "net_profit": net_profit,
            "net_margin": net_margin,
            "prime_cost_pct": prime_cost_pct,
        })

    # Print comparison table
    print(f"\n── Monthly P&L ──────────────────────────────────")
    print(f"  {'Month':<10} {'Revenue':>10} {'COGS':>10} {'Labor':>10} {'Gross %':>8} {'Net':>10} {'Net %':>7}")
    print(f"  {'─' * 65}")

    for i, s in enumerate(summaries):
        rev_change = _change_indicator(s["revenue"], summaries[i-1]["revenue"]) if i > 0 else ""
        print(f"  {s['month']:<10} {s['revenue']:>10,.0f} {s['cogs']:>10,.0f} {s['labor']:>10,.0f} {s['gross_margin']:>7.1f}% {s['net_profit']:>10,.0f} {s['net_margin']:>6.1f}%{rev_change}")

    # Highlight significant changes
    alerts = []
    for i in range(1, len(summaries)):
        curr = summaries[i]
        prev = summaries[i - 1]

        if prev["revenue"] and abs((curr["revenue"] - prev["revenue"]) / prev["revenue"]) > 0.10:
            pct = ((curr["revenue"] - prev["revenue"]) / prev["revenue"]) * 100
            direction = "up" if pct > 0 else "down"
            alerts.append(f"Revenue {direction} {abs(pct):.0f}% in {curr['month']} vs {prev['month']}")

        if prev["cogs"] and abs((curr["cogs"] - prev["cogs"]) / prev["cogs"]) > 0.15:
            pct = ((curr["cogs"] - prev["cogs"]) / prev["cogs"]) * 100
            direction = "up" if pct > 0 else "down"
            alerts.append(f"COGS {direction} {abs(pct):.0f}% in {curr['month']} vs {prev['month']}")

        if prev["labor"] and abs((curr["labor"] - prev["labor"]) / prev["labor"]) > 0.15:
            pct = ((curr["labor"] - prev["labor"]) / prev["labor"]) * 100
            direction = "up" if pct > 0 else "down"
            alerts.append(f"Labor costs {direction} {abs(pct):.0f}% in {curr['month']} vs {prev['month']}")

    if alerts:
        print(f"\n── Significant Changes (>10%) ───────────────────")
        for alert in alerts:
            print(f"  ! {alert}")
    else:
        print(f"\n  No significant month-over-month swings detected.")

    # Prime cost trend
    print(f"\n── Prime Cost Trend ─────────────────────────────")
    for s in summaries:
        bar_len = int(s["prime_cost_pct"] / 2)
        bar = "#" * bar_len
        marker = " <-- above 65%" if s["prime_cost_pct"] > 65 else ""
        print(f"  {s['month']}  {s['prime_cost_pct']:>5.1f}%  {bar}{marker}")

    # Save report
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "date": today.isoformat(),
        "months_compared": months,
        "summaries": summaries,
        "alerts": alerts,
    }
    path = DATA_DIR / f"monthly_comparison_{today.isoformat()}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved: {path}")

    # Log
    try:
        from log import log_action
        log_action("workflow", f"Monthly comparison: {len(summaries)} months compared, {len(alerts)} alerts",
                   details={"months": [s["month"] for s in summaries], "alerts": len(alerts)})
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monthly P&L comparison")
    parser.add_argument("--months", type=int, default=3, help="Number of months to compare (default: 3)")
    args = parser.parse_args()
    main(months=args.months)
