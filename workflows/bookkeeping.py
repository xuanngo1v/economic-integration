#!/usr/bin/env python3
"""
Workflow: Bookkeeping Assistant
=================================
The main bookkeeping workflow. Helps create journal entries for common
accounting tasks — supplier invoices, expenses, revenue, corrections.

How it works:
  1. Ask what needs to be booked
  2. Look up the right accounts from your chart of accounts
  3. Show a preview with account names, amounts, VAT
  4. Ask for confirmation
  5. POST the entry to e-conomic as a journal voucher
  6. Log the action

The entry goes into the journal as an UNBOOKED voucher.
Your accountant reviews and finalizes it in e-conomic.

⚠ WRITE operation — always shows preview, always asks before creating.

Usage:
  python workflows/bookkeeping.py --interactive
  python workflows/bookkeeping.py --type supplier-invoice
  python workflows/bookkeeping.py --type expense
  python workflows/bookkeeping.py --type revenue
"""

import argparse
import json
import requests
import sys
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH
from account_map import map_account_category, CATEGORY_LABELS


def load_schema():
    if SCHEMA_PATH.exists():
        return json.loads(SCHEMA_PATH.read_text())
    return {}


def lookup_account(schema, number):
    """Look up account name from schema."""
    return schema.get("accounts", {}).get("lookup", {}).get(str(number), {})


def lookup_supplier(schema, number):
    """Look up supplier name from schema."""
    return schema.get("suppliers", {}).get("lookup", {}).get(str(number), {})


# ---------------------------------------------------------------------------
# Entry types
# ---------------------------------------------------------------------------

def supplier_invoice_flow(schema):
    """Book a supplier invoice."""
    print("\n── Supplier Invoice ─────────────────────────────")
    print("  This creates an entry for a bill you received from a supplier.\n")

    # List suppliers
    suppliers = schema.get("suppliers", {}).get("lookup", {})
    if suppliers:
        print("  Your suppliers (top 15):")
        sorted_suppliers = sorted(suppliers.values(), key=lambda x: x.get("number", 0))
        for s in sorted_suppliers[:15]:
            print(f"    #{s['number']:<10} {s.get('name', '')}")
        if len(sorted_suppliers) > 15:
            print(f"    ... and {len(sorted_suppliers) - 15} more")
        print()

    supplier_num = input("  Supplier number: ").strip()
    if not supplier_num:
        print("  Cancelled.")
        return None

    supplier_info = lookup_supplier(schema, supplier_num)
    supplier_name = supplier_info.get("name", f"Supplier #{supplier_num}")
    print(f"  → {supplier_name}")

    invoice_num = input("  Invoice number (from the supplier): ").strip()
    amount_str = input("  Amount incl. VAT (e.g. 5000): ").strip()
    description = input("  Description (e.g. 'Goods delivery January'): ").strip()
    entry_date = input(f"  Date (YYYY-MM-DD, default today {date.today().isoformat()}): ").strip()
    if not entry_date:
        entry_date = date.today().isoformat()

    try:
        amount = float(amount_str)
    except ValueError:
        print("  Invalid amount.")
        return None

    # Determine expense account
    print("\n  Which expense account? Common ones:")
    expense_accounts = []
    for num_str, info in sorted(schema.get("accounts", {}).get("lookup", {}).items(), key=lambda x: int(x[0])):
        cat = map_account_category(int(num_str))
        if cat in ("cogs", "premises", "admin", "platform_fees", "transport") and info.get("type") == "profitAndLoss":
            expense_accounts.append(info)
    for a in expense_accounts[:15]:
        cat = map_account_category(a["number"])
        print(f"    {a['number']:>6}  {a['name']:<40} ({CATEGORY_LABELS.get(cat, cat)})")
    if len(expense_accounts) > 15:
        print(f"    ... and {len(expense_accounts) - 15} more")

    expense_acct = input("\n  Expense account number: ").strip()
    if not expense_acct:
        print("  Cancelled.")
        return None

    expense_info = lookup_account(schema, expense_acct)

    # Determine journal
    journals = schema.get("journals", {}).get("journals", [])
    # Prefer journal 6 (supplier invoices) or ask
    default_journal = 6
    journal_names = {j["number"]: j["name"] for j in journals}
    print(f"\n  Journal: {default_journal} ({journal_names.get(default_journal, '?')})")
    journal_override = input(f"  Press Enter for journal {default_journal}, or type another number: ").strip()
    journal_num = int(journal_override) if journal_override else default_journal

    # VAT
    vat_code = "I25"  # Standard 25% purchase VAT
    print(f"  VAT: {vat_code} (25% purchase VAT)")
    vat_override = input("  Press Enter for I25, or type another code: ").strip()
    if vat_override:
        vat_code = vat_override

    return {
        "type": "supplierInvoice",
        "journal": journal_num,
        "entry": {
            "supplier": {"supplierNumber": int(supplier_num)},
            "supplierInvoiceNumber": invoice_num,
            "date": entry_date,
            "amount": -abs(amount),  # Supplier invoices are negative (credit to supplier)
            "contraAccount": {"accountNumber": int(expense_acct)},
            "contraVatAccount": {"vatCode": vat_code},
            "currency": {"code": "?"},
            "text": description or f"{supplier_name} - {invoice_num}",
        },
        "display": {
            "supplier": supplier_name,
            "invoice": invoice_num,
            "amount": amount,
            "expense_account": f"{expense_acct} ({expense_info.get('name', '?')})",
            "vat": vat_code,
            "journal": f"{journal_num} ({journal_names.get(journal_num, '?')})",
            "date": entry_date,
            "description": description,
        },
    }


def expense_flow(schema):
    """Book a general expense (finance voucher)."""
    print("\n── General Expense (Finanspostering) ────────────")
    print("  This creates a finance voucher for an expense.\n")

    description = input("  What is this expense? (e.g. 'Software subscription March'): ").strip()
    amount_str = input("  Amount incl. VAT: ").strip()
    entry_date = input(f"  Date (default {date.today().isoformat()}): ").strip() or date.today().isoformat()

    try:
        amount = float(amount_str)
    except ValueError:
        print("  Invalid amount.")
        return None

    # Expense account
    print("\n  Expense account:")
    for num_str, info in sorted(schema.get("accounts", {}).get("lookup", {}).items(), key=lambda x: int(x[0])):
        cat = map_account_category(int(num_str))
        if cat in ("cogs", "premises", "admin", "platform_fees", "transport") and info.get("type") == "profitAndLoss":
            print(f"    {info['number']:>6}  {info['name']}")
    expense_acct = input("\n  Account number: ").strip()
    if not expense_acct:
        return None

    # Contra account (usually bank)
    print("\n  Paid from (contra account):")
    for num_str, info in sorted(schema.get("accounts", {}).get("lookup", {}).items(), key=lambda x: int(x[0])):
        if info.get("type") == "status" and ("bank" in info.get("name", "").lower() or "cash" in info.get("name", "").lower() or "kasse" in info.get("name", "").lower()):
            print(f"    {info['number']:>6}  {info['name']}")
    contra_acct = input("\n  Contra account number: ").strip()
    if not contra_acct:
        return None

    expense_info = lookup_account(schema, expense_acct)
    contra_info = lookup_account(schema, contra_acct)

    # Journal — prefer 7 (Daglig) for general expenses
    journal_num = 7
    journals = {j["number"]: j["name"] for j in schema.get("journals", {}).get("journals", [])}
    override = input(f"  Journal (default {journal_num} - {journals.get(journal_num, '?')}): ").strip()
    if override:
        journal_num = int(override)

    return {
        "type": "financeVoucher",
        "journal": journal_num,
        "entry": {
            "account": {"accountNumber": int(expense_acct)},
            "amount": abs(amount),
            "contraAccount": {"accountNumber": int(contra_acct)},
            "currency": {"code": "?"},
            "date": entry_date,
            "text": description,
        },
        "display": {
            "expense_account": f"{expense_acct} ({expense_info.get('name', '?')})",
            "contra_account": f"{contra_acct} ({contra_info.get('name', '?')})",
            "amount": amount,
            "journal": f"{journal_num} ({journals.get(journal_num, '?')})",
            "date": entry_date,
            "description": description,
        },
    }


# ---------------------------------------------------------------------------
# Preview & Confirm
# ---------------------------------------------------------------------------

def preview_and_confirm(prepared: dict) -> bool:
    """Show what will be created and ask for confirmation."""
    display = prepared["display"]
    entry_type = prepared["type"]

    print("\n══ Preview ══════════════════════════════════════")
    print(f"  Type:        {entry_type}")
    for key, val in display.items():
        label = key.replace("_", " ").title()
        if key == "amount":
            print(f"  {label:<14} {val:,.2f}")
        else:
            print(f"  {label:<14} {val}")

    print()
    print("  This creates an UNBOOKED entry in the journal.")
    print("  Your accountant reviews and books it in e-conomic.")
    print()

    confirm = input("  Create this entry? (yes/no): ").strip().lower()
    return confirm in ("yes", "y", "ja")


# ---------------------------------------------------------------------------
# POST to e-conomic
# ---------------------------------------------------------------------------

def create_entry(prepared: dict) -> bool:
    """POST the entry to the journal."""
    journal_num = prepared["journal"]
    entry_type = prepared["type"]
    entry_data = prepared["entry"]

    # Build the voucher payload
    if entry_type == "supplierInvoice":
        payload = {
            "entries": {
                "supplierInvoices": [entry_data]
            }
        }
    else:
        # financeVoucher
        payload = {
            "entries": {
                "financeVouchers": [entry_data]
            }
        }

    r = requests.post(
        f"{BASE_URL}/journals/{journal_num}/vouchers",
        headers=headers(),
        json=payload,
        timeout=30,
    )

    if r.status_code in (200, 201):
        result = r.json()
        voucher_num = result.get("voucherNumber", "?")
        print(f"\n  Entry created — voucher #{voucher_num} in journal {journal_num}")
        print(f"  Status: UNBOOKED — waiting for accountant to review and book.")

        # Log it
        try:
            from log import log_action
            log_action(
                "bookkeeping",
                f"Created {entry_type} voucher #{voucher_num} in journal {journal_num}: {prepared['display'].get('description', '')} ({prepared['display']['amount']:,.0f})",
                details=prepared["display"],
                requires_review=True,
            )
        except Exception:
            pass

        return True
    else:
        print(f"\n  Failed: HTTP {r.status_code}")
        try:
            err = r.json()
            print(f"  {err.get('message', '')}")
            hint = err.get("developerHint", "")
            if hint:
                print(f"  Hint: {hint}")
            # Show field-level errors if present
            errors = err.get("errors", {})
            if errors:
                for field, details in errors.items():
                    print(f"  {field}: {details}")
        except Exception:
            print(f"  {r.text[:300]}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ENTRY_TYPES = {
    "supplier-invoice": ("Supplier Invoice", supplier_invoice_flow),
    "expense": ("General Expense", expense_flow),
}


def main():
    print("Bookkeeping Assistant")
    print("=" * 55)
    print("Creates journal entries in e-conomic for your accountant to review.\n")

    schema = load_schema()
    if not schema:
        print("No schema.json found. Run: python schema.py")
        print("The schema is needed to look up accounts and suppliers.")
        return

    parser = argparse.ArgumentParser(description="Bookkeeping assistant")
    parser.add_argument("--type", choices=list(ENTRY_TYPES.keys()),
                        help="Entry type to create")
    parser.add_argument("--interactive", action="store_true",
                        help="Interactive mode (choose type)")
    args = parser.parse_args()

    if args.type:
        _, flow_fn = ENTRY_TYPES[args.type]
        prepared = flow_fn(schema)
    else:
        # Interactive — choose type
        print("What do you want to book?\n")
        for i, (key, (label, _)) in enumerate(ENTRY_TYPES.items(), 1):
            print(f"  {i}. {label}")
        print()
        choice = input("Choose (1/2): ").strip()

        keys = list(ENTRY_TYPES.keys())
        try:
            idx = int(choice) - 1
            _, flow_fn = ENTRY_TYPES[keys[idx]]
        except (ValueError, IndexError):
            print("Invalid choice.")
            return

        prepared = flow_fn(schema)

    if not prepared:
        return

    if preview_and_confirm(prepared):
        create_entry(prepared)
    else:
        print("  Cancelled. Nothing was created.")


if __name__ == "__main__":
    main()
