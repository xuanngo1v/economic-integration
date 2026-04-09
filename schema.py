#!/usr/bin/env python3
"""
e-conomic Schema Index
========================
Builds a fast-reference index of your e-conomic setup:
  - API endpoints and what they return
  - Your chart of accounts (numbered + categorized)
  - Journals and their purpose
  - Supplier/customer/product counts and key IDs
  - Payment terms and VAT codes

Saves to data/schema.json — a single file that agents and scripts can
read instantly instead of making API calls every time.

Run this after explore.py, or on its own. Updates the schema in place.

Usage:
  python schema.py                # Full rebuild
  python schema.py --section accounts  # Just update accounts
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from api import get, get_all, count, BASE_URL, DATA_DIR, SCHEMA_PATH
from account_map import map_account_category

PROJECT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Schema sections
# ---------------------------------------------------------------------------

def build_company() -> dict:
    print("  Building: company...")
    data = get("/self")
    if not data:
        return {}
    company = data.get("company", {})
    return {
        "name": company.get("name", ""),
        "agreement": data.get("agreementNumber"),
        "vat_number": company.get("vatNumber", ""),
        "base_currency": (data.get("baseCurrency") or {}).get("code", "?"),
    }


def build_api_index() -> dict:
    """Document all available API endpoints."""
    print("  Building: api_index...")
    return {
        "base_url": BASE_URL,
        "endpoints": {
            "/self": {"method": "GET", "description": "Company info and agreement details"},
            "/accounts": {"method": "GET", "description": "Chart of accounts (chart of accounts)"},
            "/accounting-years": {"method": "GET/POST", "description": "Fiscal years and periods"},
            "/entries": {"method": "GET", "description": "All journal entries (filterable by date)"},
            "/journals": {"method": "GET", "description": "Journal list"},
            "/journals/{id}/vouchers": {"method": "GET/POST", "description": "Journal vouchers — POST to create entries"},
            "/journals/{id}/entries": {"method": "GET", "description": "Entries within a journal"},
            "/journals/{id}/templates/financeVoucher": {"method": "GET", "description": "Template for finance vouchers"},
            "/journals/{id}/templates/manualCustomerInvoice": {"method": "GET", "description": "Template for manual invoices"},
            "/invoices/drafts": {"method": "GET/POST", "description": "Draft invoices — POST to create new draft"},
            "/invoices/booked": {"method": "GET", "description": "All booked (finalized) invoices"},
            "/invoices/paid": {"method": "GET", "description": "Paid invoices"},
            "/invoices/unpaid": {"method": "GET", "description": "Unpaid invoices"},
            "/invoices/overdue": {"method": "GET", "description": "Overdue invoices"},
            "/invoices/sent": {"method": "GET", "description": "Sent invoices"},
            "/invoices/totals": {"method": "GET", "description": "Invoice totals/aggregations"},
            "/customers": {"method": "GET/POST", "description": "Customer records"},
            "/customer-groups": {"method": "GET/POST/PUT/DELETE", "description": "Customer categories"},
            "/suppliers": {"method": "GET/POST", "description": "Supplier records"},
            "/supplier-groups": {"method": "GET/POST/PUT/DELETE", "description": "Supplier categories"},
            "/products": {"method": "GET/POST/PUT/DELETE", "description": "Product catalog"},
            "/product-groups": {"method": "GET/POST/PUT/DELETE", "description": "Product categories"},
            "/orders/drafts": {"method": "GET/POST", "description": "Draft orders"},
            "/orders/sent": {"method": "GET", "description": "Sent orders"},
            "/orders/archived": {"method": "GET", "description": "Archived orders"},
            "/quotes": {"method": "GET/POST", "description": "Quotations"},
            "/payment-terms": {"method": "GET", "description": "Payment term definitions"},
            "/payment-types": {"method": "GET", "description": "Payment type definitions"},
            "/currencies": {"method": "GET", "description": "Available currencies"},
            "/departments": {"method": "GET", "description": "Department structure"},
            "/departmental-distributions": {"method": "GET", "description": "Cost distributions"},
            "/employees": {"method": "GET", "description": "Employee records"},
            "/layouts": {"method": "GET", "description": "Invoice/document layouts"},
            "/units": {"method": "GET", "description": "Unit definitions (stk, kg, timer, etc.)"},
            "/vat-accounts": {"method": "GET", "description": "VAT/moms account setup"},
            "/vat-zones": {"method": "GET", "description": "VAT zone definitions"},
            "/modules": {"method": "GET", "description": "Active e-conomic modules"},
        },
        "auth": {
            "headers": ["X-AppSecretToken", "X-AgreementGrantToken"],
            "roles": ["SuperUser", "Bookkeeping", "Sales", "ProjectEmployee"],
        },
        "pagination": {
            "max_pagesize": 1000,
            "default_pagesize": 20,
            "follow": "pagination.nextPage",
        },
        "filtering": {
            "syntax": "filter=field$operator$value",
            "operators": ["eq", "ne", "gt", "gte", "lt", "lte", "like", "in"],
            "combine": "$and: / $or:",
            "example": "filter=date$gte$2026-01-01$and$date$lte$2026-03-31",
        },
    }


def build_accounts() -> dict:
    """Full chart of accounts with categories."""
    print("  Building: accounts...")
    accounts = get_all("/accounts", params={"pagesize": 500})

    lookup = {}
    by_category = {}
    for a in accounts:
        num = a.get("accountNumber")
        name = a.get("name", "")
        atype = a.get("accountType", "")
        cat = _categorize(num)

        entry = {"number": num, "name": name, "type": atype, "category": cat}
        if num is not None:
            lookup[str(num)] = entry
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(entry)

    return {
        "total": len(accounts),
        "lookup": lookup,
        "by_category": by_category,
        "category_ranges": {
            "revenue": "1000-1999",
            "cogs": "2000-2999",
            "labor": "3000-3999",
            "premises": "4000-4299",
            "transport": "4300-4399",
            "platform_fees": "4400-4599",
            "other_ops": "4600-4699",
            "admin": "4700-4999",
            "depreciation": "5000-5499",
            "financial_income": "5500-5599",
            "financial_expense": "5600-5999",
            "tax": "6000-6999",
            "balance_sheet": "7000+",
        },
    }


def build_journals() -> dict:
    print("  Building: journals...")
    journals = get_all("/journals", params={"pagesize": 50})
    return {
        "count": len(journals),
        "journals": [{
            "number": j.get("journalNumber"),
            "name": j.get("name", ""),
            "restriction": j.get("entryTypeRestricted", ""),
        } for j in journals],
    }


def build_suppliers() -> dict:
    print("  Building: suppliers...")
    suppliers = get_all("/suppliers", params={"pagesize": 500})
    return {
        "count": len(suppliers),
        "lookup": {
            str(s.get("supplierNumber")): {
                "number": s.get("supplierNumber"),
                "name": s.get("name", ""),
                "city": s.get("city", ""),
            } for s in suppliers
        },
    }


def build_customers() -> dict:
    print("  Building: customers...")
    customers = get_all("/customers", params={"pagesize": 500})
    return {
        "count": len(customers),
        "lookup": {
            str(c.get("customerNumber")): {
                "number": c.get("customerNumber"),
                "name": c.get("name", ""),
                "city": c.get("city", ""),
            } for c in customers
        },
    }


def build_products() -> dict:
    print("  Building: products...")
    products = get_all("/products", params={"pagesize": 500})
    return {
        "count": len(products),
        "lookup": {
            str(p.get("productNumber")): {
                "number": p.get("productNumber"),
                "name": p.get("name", ""),
                "sales_price": p.get("salesPrice"),
            } for p in products
        },
    }


def build_payment_terms() -> dict:
    print("  Building: payment_terms...")
    terms = get_all("/payment-terms", params={"pagesize": 100})
    return {
        "count": len(terms),
        "terms": [{
            "number": t.get("paymentTermsNumber"),
            "name": t.get("name", ""),
            "type": t.get("paymentTermsType", ""),
            "days": t.get("daysOfCredit"),
        } for t in terms],
    }


def build_vat() -> dict:
    print("  Building: vat...")
    vat = get_all("/vat-accounts", params={"pagesize": 100})
    return {
        "count": len(vat),
        "accounts": [{
            "code": v.get("vatCode"),
            "name": v.get("name", ""),
            "rate": v.get("ratePercentage"),
        } for v in vat],
    }


def build_counts() -> dict:
    """Quick count of key resources for status overview."""
    print("  Building: counts...")
    return {
        "invoices_booked": count("/invoices/booked"),
        "invoices_drafts": count("/invoices/drafts"),
        "invoices_unpaid": count("/invoices/unpaid"),
        "invoices_overdue": count("/invoices/overdue"),
        "suppliers": count("/suppliers"),
        "customers": count("/customers"),
        "products": count("/products"),
    }


def _categorize(num):
    return map_account_category(num)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SECTIONS = {
    "company": build_company,
    "api_index": build_api_index,
    "accounts": build_accounts,
    "journals": build_journals,
    "suppliers": build_suppliers,
    "customers": build_customers,
    "products": build_products,
    "payment_terms": build_payment_terms,
    "vat": build_vat,
    "counts": build_counts,
}


def main(section: str | None = None):
    today = date.today().isoformat()
    print(f"Building schema index — {today}")

    # Load existing schema if updating one section
    schema = {}
    if section and SCHEMA_PATH.exists():
        schema = json.loads(SCHEMA_PATH.read_text())

    if section:
        if section not in SECTIONS:
            print(f"Unknown section: {section}. Available: {', '.join(SECTIONS.keys())}")
            sys.exit(1)
        schema[section] = SECTIONS[section]()
    else:
        for name, fn in SECTIONS.items():
            schema[name] = fn()

    schema["_meta"] = {
        "last_updated": today,
        "version": "1.0",
        "description": "Fast-reference index of e-conomic setup. Read this instead of calling the API for lookups.",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCHEMA_PATH, "w") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nSchema saved: {SCHEMA_PATH}")
    print(f"Sections: {', '.join(k for k in schema if k != '_meta')}")

    # Print quick summary
    if "counts" in schema:
        c = schema["counts"]
        print(f"\nQuick status:")
        print(f"  Booked invoices: {c.get('invoices_booked', '?')}")
        print(f"  Unpaid: {c.get('invoices_unpaid', '?')}")
        print(f"  Overdue: {c.get('invoices_overdue', '?')}")
        print(f"  Suppliers: {c.get('suppliers', '?')}")
        print(f"  Customers: {c.get('customers', '?')}")
        print(f"  Products: {c.get('products', '?')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build e-conomic schema index")
    parser.add_argument("--section", choices=list(SECTIONS.keys()),
                        help="Rebuild only one section")
    args = parser.parse_args()
    main(section=args.section)
