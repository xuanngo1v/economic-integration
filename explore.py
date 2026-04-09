#!/usr/bin/env python3
"""
e-conomic Explorer
====================
Maps out your entire e-conomic setup so an AI agent (or you) can understand
how your accounting is structured before doing anything.

This is READ-ONLY. It never creates, modifies, or deletes anything.

What it maps:
  - Company info (name, agreement, VAT number)
  - Chart of accounts (how your accountant organized things)
  - Active journals (where entries are posted)
  - Suppliers & customers (who you do business with)
  - Products (what you sell)
  - Payment terms (how you get paid / pay others)
  - VAT setup (moms configuration)
  - Invoice status (drafts, unpaid, overdue)
  - Recent journal activity

Output:
  data/explorer_report_YYYY-MM-DD.json   (full structured data)
  Terminal summary in plain language

Usage:
  python explore.py
  python explore.py --section accounts    # Only map chart of accounts
  python explore.py --section invoices    # Only check invoice status
"""

import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from api import get, get_all, DATA_DIR
from account_map import map_account_category

PROJECT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Section: Company
# ---------------------------------------------------------------------------

def explore_company() -> dict:
    """Who is this e-conomic agreement for?"""
    print("\n══ Company ══════════════════════════════════════")
    data = get("/self")
    if not data:
        print("  Could not fetch company info.")
        return {}

    company = data.get("company", {})
    info = {
        "name": company.get("name", "Unknown"),
        "agreement_number": data.get("agreementNumber"),
        "vat_number": company.get("vatNumber", ""),
        "company_number": company.get("companyNumber"),
        "base_currency": (data.get("baseCurrency") or {}).get("code", "?"),
        "modules": [m.get("name", "") if isinstance(m, dict) else str(m) for m in (data.get("modules", {}).get("collection", []) if isinstance(data.get("modules"), dict) else (data.get("modules") or []))],
    }

    print(f"  Company:    {info['name']}")
    print(f"  Agreement:  {info['agreement_number']}")
    print(f"  VAT number: {info['vat_number']}")
    print(f"  Currency:   {info['base_currency']}")
    if info["modules"]:
        print(f"  Modules:    {', '.join(info['modules'])}")

    return info


# ---------------------------------------------------------------------------
# Section: Chart of Accounts
# ---------------------------------------------------------------------------

def explore_accounts() -> dict:
    """How has the accountant structured the chart of accounts?"""
    print("\n══ Chart of Accounts ════════════════════════════")
    accounts = get_all("/accounts", params={"pagesize": 500})

    if not accounts:
        print("  No accounts found.")
        return {"accounts": [], "summary": {}}

    # Categorize
    categories = defaultdict(list)
    headings = []
    for a in accounts:
        num = a.get("accountNumber")
        name = a.get("name", "")
        atype = a.get("accountType", "")

        if atype == "heading":
            headings.append({"number": num, "name": name})
        else:
            # Group by thousand range
            if num is not None:
                group = (num // 1000) * 1000
                categories[group].append({
                    "number": num,
                    "name": name,
                    "type": atype,
                })

    # Print structure
    print(f"  Total accounts: {len(accounts)}")
    print(f"  Headings: {len(headings)}")
    print()
    print("  Account structure (by range):")
    for group in sorted(categories.keys()):
        accts = categories[group]
        label = _describe_range(group)
        print(f"    {group}-{group+999}: {len(accts)} accounts  ({label})")

    if headings:
        print()
        print("  Main sections (headings):")
        for h in headings[:15]:
            print(f"    {h['number']:>6}  {h['name']}")
        if len(headings) > 15:
            print(f"    ... and {len(headings) - 15} more")

    return {
        "total": len(accounts),
        "headings": headings,
        "by_range": {str(k): v for k, v in categories.items()},
    }


def _describe_range(group: int) -> str:
    """Describe account range in plain language."""
    ranges = {
        1000: "Revenue",
        2000: "Cost of goods (COGS)",
        3000: "Staff costs (Labor)",
        4000: "Operating expenses (Premises, Transport, Fees, Admin)",
        5000: "Depreciation / Financial items",
        6000: "Tax",
        7000: "Balance sheet",
        8000: "Balance sheet",
        9000: "Balance sheet",
    }
    return ranges.get(group, "Other")


# ---------------------------------------------------------------------------
# Section: Journals
# ---------------------------------------------------------------------------

def explore_journals() -> dict:
    """What journals exist and what are they used for?"""
    print("\n══ Journals ═════════════════════════════════════")
    journals = get_all("/journals", params={"pagesize": 100})

    if not journals:
        print("  No journals found.")
        return {"journals": []}

    records = []
    for j in journals:
        rec = {
            "number": j.get("journalNumber"),
            "name": j.get("name", ""),
            "entry_type_restricted": j.get("entryTypeRestricted", ""),
            "min_voucher": j.get("settings", {}).get("minVoucherNumber") if isinstance(j.get("settings"), dict) else None,
        }
        records.append(rec)
        restriction = rec["entry_type_restricted"] or "all types"
        print(f"  Journal {rec['number']}: {rec['name']} ({restriction})")

    return {"journals": records}


# ---------------------------------------------------------------------------
# Section: Suppliers
# ---------------------------------------------------------------------------

def explore_suppliers() -> dict:
    """Who do you buy from?"""
    print("\n══ Suppliers ════════════════════════════════════")
    suppliers = get_all("/suppliers", params={"pagesize": 500})

    if not suppliers:
        print("  No suppliers found.")
        return {"count": 0, "suppliers": []}

    records = []
    for s in suppliers:
        records.append({
            "number": s.get("supplierNumber"),
            "name": s.get("name", ""),
            "email": s.get("email", ""),
            "city": s.get("city", ""),
        })

    print(f"  Total suppliers: {len(records)}")
    print()
    print("  Top suppliers:")
    for s in records[:10]:
        city = f" ({s['city']})" if s['city'] else ""
        print(f"    #{s['number']:<6} {s['name']}{city}")
    if len(records) > 10:
        print(f"    ... and {len(records) - 10} more")

    return {"count": len(records), "suppliers": records}


# ---------------------------------------------------------------------------
# Section: Customers
# ---------------------------------------------------------------------------

def explore_customers() -> dict:
    """Who do you sell to?"""
    print("\n══ Customers ════════════════════════════════════")
    customers = get_all("/customers", params={"pagesize": 500})

    if not customers:
        print("  No customers found.")
        return {"count": 0, "customers": []}

    records = []
    for c in customers:
        records.append({
            "number": c.get("customerNumber"),
            "name": c.get("name", ""),
            "email": c.get("email", ""),
            "city": c.get("city", ""),
        })

    print(f"  Total customers: {len(records)}")
    print()
    print("  Customers:")
    for c in records[:10]:
        city = f" ({c['city']})" if c['city'] else ""
        print(f"    #{c['number']:<6} {c['name']}{city}")
    if len(records) > 10:
        print(f"    ... and {len(records) - 10} more")

    return {"count": len(records), "customers": records}


# ---------------------------------------------------------------------------
# Section: Products
# ---------------------------------------------------------------------------

def explore_products() -> dict:
    """What products/services are registered?"""
    print("\n══ Products ═════════════════════════════════════")
    products = get_all("/products", params={"pagesize": 500})

    if not products:
        print("  No products found.")
        return {"count": 0, "products": []}

    records = []
    for p in products:
        records.append({
            "number": p.get("productNumber"),
            "name": p.get("name", ""),
            "sales_price": p.get("salesPrice"),
            "cost_price": p.get("costPrice"),
            "unit": (p.get("unit") or {}).get("name", ""),
        })

    print(f"  Total products: {len(records)}")
    for p in records[:10]:
        price = f"  {p['sales_price']:.2f}" if p['sales_price'] else ""
        print(f"    {p['number']:<10} {p['name']}{price}")
    if len(records) > 10:
        print(f"    ... and {len(records) - 10} more")

    return {"count": len(records), "products": records}


# ---------------------------------------------------------------------------
# Section: Invoice Status
# ---------------------------------------------------------------------------

def explore_invoices() -> dict:
    """What's the current invoice situation?"""
    print("\n══ Invoice Status ═══════════════════════════════")

    drafts = get("/invoices/drafts", params={"pagesize": 1})
    booked = get("/invoices/booked", params={"pagesize": 1})
    unpaid = get("/invoices/unpaid", params={"pagesize": 1})
    overdue = get("/invoices/overdue", params={"pagesize": 1})

    def count(data):
        if data and "pagination" in data:
            return data["pagination"].get("results", 0)
        return 0

    status = {
        "drafts": count(drafts),
        "booked_total": count(booked),
        "unpaid": count(unpaid),
        "overdue": count(overdue),
    }

    print(f"  Draft invoices:   {status['drafts']}")
    print(f"  Booked (total):   {status['booked_total']}")
    print(f"  Unpaid:           {status['unpaid']}")
    print(f"  Overdue:          {status['overdue']}")

    if status["overdue"] > 0:
        print(f"\n  ⚠ You have {status['overdue']} overdue invoices that need attention.")

    return status


# ---------------------------------------------------------------------------
# Section: Payment Terms
# ---------------------------------------------------------------------------

def explore_payment_terms() -> dict:
    """How are payment terms configured?"""
    print("\n══ Payment Terms ════════════════════════════════")
    terms = get_all("/payment-terms", params={"pagesize": 100})

    if not terms:
        print("  No payment terms found.")
        return {"terms": []}

    records = []
    for t in terms:
        records.append({
            "number": t.get("paymentTermsNumber"),
            "name": t.get("name", ""),
            "type": t.get("paymentTermsType", ""),
            "days": t.get("daysOfCredit"),
        })
        days = f"{t.get('daysOfCredit', '?')} days" if t.get('daysOfCredit') else t.get('paymentTermsType', '')
        print(f"    {t.get('name', 'Unknown'):<30} {days}")

    return {"terms": records}


# ---------------------------------------------------------------------------
# Section: VAT
# ---------------------------------------------------------------------------

def explore_vat() -> dict:
    """How is VAT/moms set up?"""
    print("\n══ VAT Accounts ═════════════════════════════════")
    vat = get_all("/vat-accounts", params={"pagesize": 100})

    if not vat:
        print("  No VAT accounts found.")
        return {"vat_accounts": []}

    records = []
    for v in vat:
        records.append({
            "code": v.get("vatCode"),
            "name": v.get("name", ""),
            "rate": v.get("ratePercentage"),
            "type": v.get("vatType", ""),
        })
        rate = f"{v.get('ratePercentage', '?')}%" if v.get('ratePercentage') is not None else ""
        print(f"    {v.get('vatCode', '?'):<6} {v.get('name', ''):<30} {rate}")

    return {"vat_accounts": records}


# ---------------------------------------------------------------------------
# Section: Recent Activity
# ---------------------------------------------------------------------------

def explore_recent_entries() -> dict:
    """What's been happening in the books recently?"""
    print("\n══ Recent Activity (last 30 days) ═══════════════")
    since = (date.today() - timedelta(days=30)).isoformat()
    entries = get_all("/entries", params={"pagesize": 1000, "filter": f"date$gte${since}"})

    if not entries:
        print("  No entries in the last 30 days.")
        return {"count": 0, "by_type": {}}

    # Summarize by account category
    by_category = defaultdict(lambda: {"count": 0, "total": 0.0})
    for e in entries:
        acct = e.get("account") or {}
        num = acct.get("accountNumber") if isinstance(acct, dict) else None
        cat = _categorize(num)
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += abs(e.get("amount", 0) or 0)

    print(f"  Total entries: {len(entries)}")
    print()
    for cat in ["revenue", "cogs", "labor", "premises", "platform_fees", "admin", "other"]:
        if cat in by_category:
            d = by_category[cat]
            print(f"    {cat:<15} {d['count']:>5} entries  {d['total']:>12,.0f}")

    return {
        "count": len(entries),
        "by_type": {k: v for k, v in by_category.items()},
    }


def _categorize(account_number) -> str:
    return map_account_category(account_number)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_report(report: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = DATA_DIR / f"explorer_report_{today}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SECTIONS = {
    "company": explore_company,
    "accounts": explore_accounts,
    "journals": explore_journals,
    "suppliers": explore_suppliers,
    "customers": explore_customers,
    "products": explore_products,
    "invoices": explore_invoices,
    "payment_terms": explore_payment_terms,
    "vat": explore_vat,
    "recent": explore_recent_entries,
}


def main(section: str | None = None) -> dict:
    today = date.today().isoformat()
    print(f"e-conomic Explorer — {today}")
    print("This is READ-ONLY. Nothing will be created or changed.")

    report = {"date": today, "sections": {}}

    if section:
        if section not in SECTIONS:
            print(f"Unknown section: {section}")
            print(f"Available: {', '.join(SECTIONS.keys())}")
            sys.exit(1)
        report["sections"][section] = SECTIONS[section]()
    else:
        for name, fn in SECTIONS.items():
            report["sections"][name] = fn()

    path = save_report(report)
    print(f"\n══ Report saved ═════════════════════════════════")
    print(f"  {path}")
    print()

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Explore your e-conomic setup (read-only)")
    parser.add_argument("--section", choices=list(SECTIONS.keys()),
                        help="Explore only one section")
    args = parser.parse_args()
    main(section=args.section)
