#!/usr/bin/env python3
"""
e-conomic Financial Data Fetcher
==================================
Fetches booked invoices, suppliers, journal entries, and chart of accounts
from the e-conomic REST API (Visma e-conomic).

Auth:
  X-AppSecretToken      = ECONOMIC_APP_SECRET  (from .env)
  X-AgreementGrantToken = ECONOMIC_AGREEMENT_TOKEN

Endpoints:
  GET /invoices/booked  -> supplier invoices (COGS/spend)
  GET /suppliers        -> supplier directory
  GET /entries          -> journal entries (P&L data)
  GET /accounts         -> chart of accounts

Output:
  data/economic_invoices_YYYY-MM-DD.json
  data/economic_suppliers_YYYY-MM-DD.json
  data/economic_entries_YYYY-MM-DD.json
  data/economic_accounts_YYYY-MM-DD.json

Usage:
  python fetch.py
  python fetch.py --days 180
"""

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from api import headers, get_all, BASE_URL, DATA_DIR
from account_map import map_account_category

PROJECT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Pagination (uses shared API but needs raise_for_status variant)
# ---------------------------------------------------------------------------

def fetch_all_pages(url: str, params: dict | None = None) -> list[dict]:
    """Follow nextPage pagination, returning all collected items.
    Raises on HTTP errors (unlike the safe get_all in api.py).
    """
    import requests
    hdrs = headers()
    items: list[dict] = []
    next_url: str | None = url

    while next_url:
        r = requests.get(next_url, headers=hdrs, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("collection", []))
        params = None
        pagination = data.get("pagination", {})
        next_url = pagination.get("nextPage")

    return items


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------

def fetch_booked_invoices() -> list[dict]:
    """GET /invoices/booked — all booked invoices, newest first."""
    print("  Fetching booked invoices...")
    items = fetch_all_pages(
        f"{BASE_URL}/invoices/booked",
        params={"pagesize": 100, "sort": "-date"},
    )
    records = []
    for inv in items:
        currency_raw = inv.get("currency", "?")
        currency = currency_raw.get("code", "?") if isinstance(currency_raw, dict) else str(currency_raw or "?")
        pt_raw = inv.get("paymentTerms") or {}
        payment_terms = pt_raw.get("name", "") if isinstance(pt_raw, dict) else str(pt_raw)
        records.append({
            "invoice_number": str(inv.get("bookedInvoiceNumber", "")),
            "supplier_name": (inv.get("recipient", {}) or {}).get("name", ""),
            "supplier_number": (inv.get("customer", {}) or {}).get("customerNumber"),
            "date": inv.get("date", ""),
            "due_date": inv.get("dueDate", ""),
            "amount": inv.get("grossAmount", 0) or 0,
            "amount_excl_vat": inv.get("netAmount", 0) or 0,
            "vat_amount": inv.get("vatAmount", 0) or 0,
            "currency": currency,
            "status": "booked",
            "payment_terms": payment_terms,
        })
    print(f"    -> {len(records)} booked invoices")
    return records


def fetch_suppliers() -> list[dict]:
    """GET /suppliers — full supplier directory."""
    print("  Fetching suppliers...")
    items = fetch_all_pages(f"{BASE_URL}/suppliers", params={"pagesize": 200})
    records = []
    for s in items:
        curr = s.get("currency", "?")
        currency = curr.get("code", "?") if isinstance(curr, dict) else str(curr or "?")
        pt = s.get("paymentTerms") or {}
        payment_terms = pt.get("name", "") if isinstance(pt, dict) else str(pt)
        records.append({
            "supplier_number": s.get("supplierNumber"),
            "name": s.get("name", ""),
            "email": s.get("email", ""),
            "phone": s.get("telephoneAndFaxNumber", ""),
            "address": s.get("address", ""),
            "city": s.get("city", ""),
            "zip": s.get("zip", ""),
            "currency": currency,
            "payment_terms": payment_terms,
        })
    print(f"    -> {len(records)} suppliers")
    return records


def fetch_entries(days: int = 90) -> list[dict]:
    """Fetch journal entries for the last N days.

    Tries /entries first, falls back to /accounting-years/{year}/entries
    since some e-conomic setups only expose entries through accounting years.
    """
    since = (date.today() - timedelta(days=days)).isoformat()
    print(f"  Fetching journal entries since {since}...")

    # Try the direct endpoint first
    items = fetch_all_pages(
        f"{BASE_URL}/entries",
        params={"pagesize": 1000, "filter": f"date$gte${since}"},
    )

    # Fallback: fetch via accounting years (some setups require this)
    if not items:
        since_date = date.today() - timedelta(days=days)
        years = set()
        d = since_date
        while d <= date.today():
            years.add(d.year)
            d = date(d.year + 1, 1, 1)
        print(f"    Trying via accounting years: {sorted(years)}...")
        for year in sorted(years):
            year_items = fetch_all_pages(
                f"{BASE_URL}/accounting-years/{year}/entries",
                params={"pagesize": 1000},
            )
            # Filter to date range
            for item in year_items:
                item_date = item.get("date", "")
                if item_date >= since:
                    items.append(item)
    records = []
    for e in items:
        acct = e.get("account") or {}
        acct_num = acct.get("accountNumber") if isinstance(acct, dict) else None
        acct_name = acct.get("name", "") if isinstance(acct, dict) else ""
        journal = e.get("journal") or {}
        journal_name = journal.get("name", "") if isinstance(journal, dict) else str(journal)
        records.append({
            "date": e.get("date", ""),
            "account_number": acct_num,
            "account_name": acct_name,
            "amount": e.get("amount", 0) or 0,
            "text": e.get("text", ""),
            "journal": journal_name,
            "voucher_number": e.get("voucherNumber"),
            "type": e.get("entryType", ""),
        })
    print(f"    -> {len(records)} journal entries")
    return records


def fetch_accounts() -> list[dict]:
    """GET /accounts — chart of accounts."""
    print("  Fetching chart of accounts...")
    items = fetch_all_pages(f"{BASE_URL}/accounts", params={"pagesize": 500})
    records = []
    for a in items:
        num = a.get("accountNumber")
        records.append({
            "account_number": num,
            "name": a.get("name", ""),
            "account_type": a.get("accountType", ""),
            "category": map_account_category(num),
        })
    print(f"    -> {len(records)} accounts")
    return records


# ---------------------------------------------------------------------------
# Summary / analytics
# ---------------------------------------------------------------------------

def _invoice_summary(invoices: list[dict]) -> dict:
    today = date.today()
    buckets = {30: 0.0, 60: 0.0, 90: 0.0}
    supplier_spend: dict[str, float] = defaultdict(float)

    for inv in invoices:
        inv_date_str = inv.get("date", "")
        if not inv_date_str:
            continue
        try:
            inv_date = date.fromisoformat(inv_date_str)
        except ValueError:
            continue
        age = (today - inv_date).days
        amount = abs(inv.get("amount", 0) or 0)
        for window in buckets:
            if age <= window:
                buckets[window] += amount
        supplier_spend[inv.get("supplier_name", "Unknown")] += amount

    top10 = sorted(supplier_spend.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "spend_last_30d": round(buckets[30], 2),
        "spend_last_60d": round(buckets[60], 2),
        "spend_last_90d": round(buckets[90], 2),
        "top_suppliers": [{"name": n, "total_amount": round(v, 2)} for n, v in top10],
    }


def _pl_summary(entries: list[dict]) -> dict:
    totals: dict[str, float] = defaultdict(float)
    for e in entries:
        cat = map_account_category(e.get("account_number"))
        totals[cat] += e.get("amount", 0) or 0

    revenue = abs(totals.get("revenue", 0))
    cogs = abs(totals.get("cogs", 0))
    labor = abs(totals.get("labor", 0))
    opex = abs(totals.get("opex", 0))
    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue else 0
    net_profit = gross_profit - labor - opex

    return {
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin_pct": round(gross_margin, 1),
        "labor": round(labor, 2),
        "opex": round(opex, 2),
        "net_profit": round(net_profit, 2),
    }


def print_summary(invoices: list[dict], entries: list[dict]) -> None:
    inv_sum = _invoice_summary(invoices)
    pl = _pl_summary(entries)

    print("\n── Supplier Spend ─────────────────────────────")
    print(f"  Last 30 days:  {inv_sum['spend_last_30d']:>12,.0f}")
    print(f"  Last 60 days:  {inv_sum['spend_last_60d']:>12,.0f}")
    print(f"  Last 90 days:  {inv_sum['spend_last_90d']:>12,.0f}")
    print("\n  Top 10 suppliers by spend:")
    for i, s in enumerate(inv_sum["top_suppliers"], 1):
        print(f"  {i:>2}. {s['name']:<35} {s['total_amount']:>10,.0f}")

    print("\n── P&L Estimate (journal entries) ────────────")
    print(f"  Revenue:       {pl['revenue']:>12,.0f}")
    print(f"  COGS:          {pl['cogs']:>12,.0f}")
    print(f"  Gross Profit:  {pl['gross_profit']:>12,.0f}  ({pl['gross_margin_pct']:.1f}%)")
    print(f"  Labor:         {pl['labor']:>12,.0f}")
    print(f"  OpEx:          {pl['opex']:>12,.0f}")
    print(f"  Net Profit:    {pl['net_profit']:>12,.0f}")
    print()


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save(filename: str, data: list | dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(days: int = 90) -> dict:
    """Fetch all e-conomic data and save to JSON. Returns the fetched data."""
    today = date.today().isoformat()
    print(f"e-conomic fetch — {today}")

    invoices = fetch_booked_invoices()
    suppliers = fetch_suppliers()
    entries = fetch_entries(days=days)
    accounts = fetch_accounts()

    p1 = save(f"economic_invoices_{today}.json", invoices)
    p2 = save(f"economic_suppliers_{today}.json", suppliers)
    p3 = save(f"economic_entries_{today}.json", entries)
    p4 = save(f"economic_accounts_{today}.json", accounts)

    print(f"\nSaved:")
    for p in (p1, p2, p3, p4):
        print(f"  {p}")

    print_summary(invoices, entries)

    return {
        "invoices": invoices,
        "suppliers": suppliers,
        "entries": entries,
        "accounts": accounts,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch financial data from e-conomic")
    parser.add_argument("--days", type=int, default=90,
                        help="Days back for journal entries (default: 90)")
    args = parser.parse_args()
    main(days=args.days)
