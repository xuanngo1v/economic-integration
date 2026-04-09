#!/usr/bin/env python3
"""
Workflow: Create Draft Invoice
================================
Creates a DRAFT invoice in e-conomic. Does NOT book it — the draft stays
in your system for review before you (or your accountant) books it.

⚠ This is a WRITE operation. It will ask for confirmation before creating.

Usage:
  python workflows/create_invoice.py --customer 1 --product 1 --quantity 10
  python workflows/create_invoice.py --interactive
"""

import argparse
import json
import requests
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def list_customers():
    """Show available customers."""
    customers = get_all("/customers", params={"pagesize": 100})
    print("\nAvailable customers:")
    for c in customers[:20]:
        print(f"  #{c.get('customerNumber'):<6} {c.get('name', '')}")
    if len(customers) > 20:
        print(f"  ... and {len(customers) - 20} more")
    return customers


def list_products():
    """Show available products."""
    products = get_all("/products", params={"pagesize": 100})
    print("\nAvailable products:")
    for p in products[:20]:
        price = p.get("salesPrice", 0)
        print(f"  #{p.get('productNumber'):<10} {p.get('name', ''):<30} {price:>8,.2f}")
    if len(products) > 20:
        print(f"  ... and {len(products) - 20} more")
    return products


def interactive_mode():
    """Guide the user through creating an invoice step by step."""
    print("Create Draft Invoice — Interactive Mode")
    print("=" * 50)
    print("This will create a DRAFT invoice. It will NOT be booked")
    print("until you or your accountant reviews and approves it.\n")

    # List customers
    customers = list_customers()
    if not customers:
        print("\nNo customers found. Create a customer in e-conomic first.")
        return

    customer_num = input("\nCustomer number: ").strip()
    if not customer_num:
        print("Cancelled.")
        return

    # List products
    products = list_products()

    lines = []
    while True:
        print(f"\nLine {len(lines) + 1}:")
        product_num = input("  Product number (or 'done' to finish): ").strip()
        if product_num.lower() == "done":
            break
        quantity = input("  Quantity: ").strip()
        price_override = input("  Unit price (press Enter to use default): ").strip()

        line = {
            "product": {"productNumber": product_num},
            "quantity": float(quantity) if quantity else 1,
        }
        if price_override:
            line["unitNetPrice"] = float(price_override)
        lines.append(line)

    if not lines:
        print("No lines added. Cancelled.")
        return

    # Build and confirm
    create_draft(int(customer_num), lines)


def create_draft(customer_number: int, lines: list[dict], payment_term_number: int | None = None):
    """Create the draft invoice after showing a preview and getting confirmation."""
    today = date.today()

    # Get default payment terms if not specified
    if not payment_term_number:
        terms = get_all("/payment-terms", params={"pagesize": 10})
        if terms:
            payment_term_number = terms[0].get("paymentTermsNumber", 1)
        else:
            payment_term_number = 1

    # Get default layout
    layouts = get_all("/layouts", params={"pagesize": 1})
    layout_number = layouts[0].get("layoutNumber", 1) if layouts else 1

    invoice_data = {
        "date": today.isoformat(),
        "currency": "?",
        "customer": {"customerNumber": customer_number},
        "paymentTerms": {"paymentTermsNumber": payment_term_number},
        "layout": {"layoutNumber": layout_number},
        "lines": lines,
    }

    # Preview
    print("\n── Invoice Preview ──────────────────────────────")
    print(f"  Customer:      #{customer_number}")
    print(f"  Date:          {today.isoformat()}")
    print(f"  Payment terms: #{payment_term_number}")
    print(f"  Lines:         {len(lines)}")
    for i, line in enumerate(lines, 1):
        prod = line.get("product", {}).get("productNumber", "?")
        qty = line.get("quantity", 1)
        price = line.get("unitNetPrice", "default")
        print(f"    {i}. Product #{prod}  x{qty}  @ {price}")

    print()
    print("  ⚠ This creates a DRAFT invoice. It will NOT be booked.")
    print("  Your accountant can review it in e-conomic before booking.")
    print()

    confirm = input("  Create this draft? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y", "ja"):
        print("  Cancelled. Nothing was created.")
        return

    # Create
    r = requests.post(
        f"{BASE_URL}/invoices/drafts",
        headers=headers(),
        json=invoice_data,
        timeout=30,
    )

    if r.status_code in (200, 201):
        result = r.json()
        draft_num = result.get("draftInvoiceNumber", "?")
        gross = result.get("grossAmount", 0)
        print(f"\n  Draft invoice #{draft_num} created — {gross:,.2f}")
        print(f"  Review it in e-conomic before booking.")
    else:
        print(f"\n  Failed: HTTP {r.status_code}")
        try:
            err = r.json()
            print(f"  {err.get('message', '')}")
            print(f"  {err.get('developerHint', '')}")
        except Exception:
            print(f"  {r.text[:300]}")


def main():
    parser = argparse.ArgumentParser(description="Create a draft invoice")
    parser.add_argument("--interactive", action="store_true", help="Guided step-by-step mode")
    parser.add_argument("--customer", type=int, help="Customer number")
    parser.add_argument("--product", help="Product number")
    parser.add_argument("--quantity", type=float, default=1, help="Quantity")
    parser.add_argument("--price", type=float, help="Override unit price")
    args = parser.parse_args()

    if args.interactive or not args.customer:
        interactive_mode()
        return

    lines = [{
        "product": {"productNumber": args.product},
        "quantity": args.quantity,
    }]
    if args.price:
        lines[0]["unitNetPrice"] = args.price

    create_draft(args.customer, lines)


if __name__ == "__main__":
    main()
