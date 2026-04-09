#!/usr/bin/env python3
"""
Knowledge Ingest — Seed the knowledge base from existing data
================================================================
Reads your fetched data (entries, invoices, suppliers, explorer report)
and extracts patterns to seed the business knowledge.

This is the "initial learn" — it gives the AI a baseline understanding
of how YOUR business does accounting before any corrections happen.

What it learns:
  - Which accounts are used most (and for what)
  - Which suppliers are most active
  - Common transaction patterns (amounts, frequencies)
  - Journal usage patterns
  - VAT code distribution

Usage:
  python knowledge/ingest.py                # Ingest latest data
  python knowledge/ingest.py --days 365     # Analyze a full year
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = KNOWLEDGE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
BUSINESS_DIR = KNOWLEDGE_DIR / "business"

sys.path.insert(0, str(PROJECT_DIR))


def _latest_file(pattern: str) -> Path | None:
    import glob
    matches = sorted(glob.glob(str(DATA_DIR / pattern)), reverse=True)
    return Path(matches[0]) if matches else None


def ingest():
    """Analyze existing data and write business knowledge."""
    today = date.today()
    print(f"Knowledge Ingest — {today.isoformat()}")
    print("=" * 55)

    # Load data
    entries_path = _latest_file("economic_entries_*.json")
    invoices_path = _latest_file("economic_invoices_*.json")
    suppliers_path = _latest_file("economic_suppliers_*.json")
    accounts_path = _latest_file("economic_accounts_*.json")

    if not entries_path or not entries_path.exists():
        print("  No entries data found. Run: python run.py")
        return

    entries = json.loads(entries_path.read_text())
    invoices = json.loads(invoices_path.read_text()) if invoices_path and invoices_path.exists() else []
    suppliers = json.loads(suppliers_path.read_text()) if suppliers_path and suppliers_path.exists() else []
    accounts = json.loads(accounts_path.read_text()) if accounts_path and accounts_path.exists() else []

    print(f"  Entries: {len(entries)}")
    print(f"  Invoices: {len(invoices)}")
    print(f"  Suppliers: {len(suppliers)}")
    print(f"  Accounts: {len(accounts)}")

    # Import account mapping
    try:
        from account_map import map_account_category, CATEGORY_LABELS
    except ImportError:
        print("  Could not import account_map.py")
        return

    # ---------------------------------------------------------------------------
    # Analyze patterns
    # ---------------------------------------------------------------------------

    # 1. Account usage frequency
    account_usage = Counter()
    account_amounts = defaultdict(float)
    for e in entries:
        num = e.get("account_number")
        if num:
            account_usage[num] += 1
            account_amounts[num] += abs(e.get("amount", 0) or 0)

    # 2. Category distribution
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    for e in entries:
        num = e.get("account_number")
        cat = map_account_category(num)
        category_totals[cat] += abs(e.get("amount", 0) or 0)
        category_counts[cat] += 1

    # 3. Journal usage
    journal_usage = Counter()
    for e in entries:
        journal = e.get("journal", "Unknown")
        journal_usage[journal] += 1

    # 4. Supplier frequency (from invoices)
    supplier_frequency = Counter()
    supplier_spend = defaultdict(float)
    for inv in invoices:
        name = inv.get("supplier_name", "Unknown")
        supplier_frequency[name] += 1
        supplier_spend[name] += abs(inv.get("amount", 0) or 0)

    # 5. Monthly revenue pattern
    monthly_revenue = defaultdict(float)
    monthly_cogs = defaultdict(float)
    for e in entries:
        month = e.get("date", "")[:7]
        num = e.get("account_number")
        cat = map_account_category(num)
        amount = abs(e.get("amount", 0) or 0)
        if cat == "revenue":
            monthly_revenue[month] += amount
        elif cat == "cogs":
            monthly_cogs[month] += amount

    # ---------------------------------------------------------------------------
    # Write patterns to knowledge
    # ---------------------------------------------------------------------------

    lines = [
        "# Learned Patterns",
        "",
        f"Auto-generated on {today.isoformat()} from transaction data.",
        f"Source: {len(entries)} entries, {len(invoices)} invoices.",
        f"Rebuild with: `python knowledge/ingest.py`",
        "",
        "## Top Accounts by Usage",
        "",
    ]

    # Build account name lookup
    account_names = {}
    for a in accounts:
        account_names[a.get("account_number")] = a.get("name", "")

    for num, count in account_usage.most_common(15):
        name = account_names.get(num, "")
        cat = map_account_category(num)
        total = account_amounts[num]
        lines.append(f"- **{num}** {name} — {count} entries, total {total:,.0f} ({cat})")

    lines.extend([
        "",
        "## Category Distribution",
        "",
        "| Category | Entries | Total Amount |",
        "|----------|---------|-------------|",
    ])

    for cat in sorted(category_totals.keys(), key=lambda c: category_totals[c], reverse=True):
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"| {label} | {category_counts[cat]} | {category_totals[cat]:,.0f} |")

    lines.extend([
        "",
        "## Journal Usage",
        "",
    ])
    for journal, count in journal_usage.most_common(10):
        lines.append(f"- **{journal}** — {count} entries")

    lines.extend([
        "",
        "## Top Suppliers",
        "",
    ])
    for name, count in supplier_frequency.most_common(10):
        spend = supplier_spend[name]
        lines.append(f"- **{name}** — {count} invoices, total {spend:,.0f}")

    if monthly_revenue:
        lines.extend([
            "",
            "## Monthly Revenue & COGS",
            "",
            "| Month | Revenue | COGS | Gross Margin |",
            "|-------|---------|------|-------------|",
        ])
        for month in sorted(monthly_revenue.keys()):
            rev = monthly_revenue[month]
            cogs = monthly_cogs.get(month, 0)
            margin = ((rev - cogs) / rev * 100) if rev else 0
            lines.append(f"| {month} | {rev:,.0f} | {cogs:,.0f} | {margin:.1f}% |")

    # Save
    patterns_path = BUSINESS_DIR / "patterns.md"
    patterns_path.write_text("\n".join(lines) + "\n")
    print(f"\n  Patterns saved: {patterns_path}")

    # Update the knowledge log
    from loader import _log
    _log(f"ingest | Baseline knowledge from {len(entries)} entries, {len(invoices)} invoices. Top account: {account_usage.most_common(1)[0][0] if account_usage else '?'}")

    # Summary
    print(f"\n── What was learned ─────────────────────────────")
    print(f"  Top accounts: {len(account_usage)} active accounts")
    print(f"  Categories: {len(category_totals)} active categories")
    print(f"  Journals: {len(journal_usage)} journals used")
    print(f"  Suppliers: {len(supplier_frequency)} active suppliers")
    if monthly_revenue:
        avg_rev = sum(monthly_revenue.values()) / len(monthly_revenue)
        print(f"  Avg monthly revenue: {avg_rev:,.0f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed knowledge base from existing data")
    args = parser.parse_args()
    ingest()
