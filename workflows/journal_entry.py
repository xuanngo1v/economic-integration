#!/usr/bin/env python3
"""
Workflow: Create Journal Entry (Finance Voucher)
===================================================
Creates a journal entry / finance voucher in e-conomic.

⚠ This is a WRITE operation. It will:
  1. Show you what it plans to create
  2. Ask for explicit confirmation
  3. Create the entry as a VOUCHER (not yet booked)

Your accountant reviews and books vouchers in e-conomic.

Usage:
  python workflows/journal_entry.py --interactive
  python workflows/journal_entry.py --journal 1 --account 3000 --amount -5000 --text "Supplier X januar"
"""

import argparse
import json
import requests
import sys
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH


def list_journals():
    journals = get_all("/journals", params={"pagesize": 50})
    print("\nAvailable journals:")
    for j in journals:
        restriction = j.get("entryTypeRestricted", "all types")
        print(f"  Journal {j.get('journalNumber')}: {j.get('name', '')} ({restriction})")
    return journals


def list_accounts_summary():
    accounts = get_all("/accounts", params={"pagesize": 500})
    print("\nAccount ranges (your chart of accounts):")
    from collections import defaultdict
    groups = defaultdict(list)
    for a in accounts:
        num = a.get("accountNumber")
        if num and a.get("accountType") != "heading":
            group = (num // 1000) * 1000
            groups[group].append(a)
    for g in sorted(groups.keys()):
        print(f"  {g}-{g+999}: {len(groups[g])} accounts")
        for a in groups[g][:3]:
            print(f"    {a['accountNumber']:>6}  {a.get('name', '')}")
        if len(groups[g]) > 3:
            print(f"    ... and {len(groups[g]) - 3} more")
    return accounts


def interactive_mode():
    print("Create Journal Entry — Interactive Mode")
    print("=" * 50)
    print("This creates a journal VOUCHER for your accountant to review.")
    print("Nothing is booked until they approve it in e-conomic.\n")

    journals = list_journals()
    if not journals:
        print("No journals found.")
        return

    journal_num = input("\nJournal number: ").strip()
    if not journal_num:
        print("Cancelled.")
        return

    list_accounts_summary()

    entries = []
    print("\nAdd entries (a voucher needs at least 2 lines that balance to 0):")
    while True:
        print(f"\nEntry {len(entries) + 1}:")
        account = input("  Account number (or 'done'): ").strip()
        if account.lower() == "done":
            break
        amount = input("  Amount (negative = debit, positive = credit): ").strip()
        text = input("  Description: ").strip()

        entries.append({
            "account": {"accountNumber": int(account)},
            "amount": float(amount),
            "text": text,
            "date": date.today().isoformat(),
        })

    if not entries:
        print("No entries. Cancelled.")
        return

    create_voucher(int(journal_num), entries)


def create_voucher(journal_number: int, entries: list[dict]):
    """Create journal voucher after confirmation."""
    total = sum(e.get("amount", 0) for e in entries)

    print("\n── Voucher Preview ──────────────────────────────")
    print(f"  Journal:  #{journal_number}")
    print(f"  Date:     {date.today().isoformat()}")
    print(f"  Lines:    {len(entries)}")
    print()
    for i, e in enumerate(entries, 1):
        acct = e.get("account", {}).get("accountNumber", "?")
        amt = e.get("amount", 0)
        txt = e.get("text", "")
        sign = "credit" if amt > 0 else "debit"
        print(f"    {i}. Account {acct}  {abs(amt):>10,.2f} ({sign})  — {txt}")

    print(f"\n  Balance: {total:,.2f}", end="")
    if abs(total) > 0.01:
        print("  ⚠ NOT BALANCED — your accountant will need to fix this")
    else:
        print("  ✓ Balanced")

    print()
    print("  ⚠ This creates a voucher for review. Your accountant books it.")
    print()

    confirm = input("  Create this voucher? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y", "ja"):
        print("  Cancelled. Nothing was created.")
        return

    # Create via finance voucher template
    voucher_data = {
        "entries": [{
            "account": e["account"],
            "amount": e["amount"],
            "text": e.get("text", ""),
            "date": e.get("date", date.today().isoformat()),
        } for e in entries]
    }

    r = requests.post(
        f"{BASE_URL}/journals/{journal_number}/vouchers",
        headers=headers(),
        json=voucher_data,
        timeout=30,
    )

    if r.status_code in (200, 201):
        print(f"\n  Voucher created in journal #{journal_number}")
        print(f"  Your accountant can review and book it in e-conomic.")
    else:
        print(f"\n  Failed: HTTP {r.status_code}")
        try:
            err = r.json()
            print(f"  {err.get('message', '')}")
            print(f"  {err.get('developerHint', '')}")
        except Exception:
            print(f"  {r.text[:300]}")


def main():
    parser = argparse.ArgumentParser(description="Create a journal entry / finance voucher")
    parser.add_argument("--interactive", action="store_true", help="Guided step-by-step mode")
    parser.add_argument("--journal", type=int, help="Journal number")
    parser.add_argument("--account", type=int, help="Account number")
    parser.add_argument("--amount", type=float, help="Amount (negative = debit)")
    parser.add_argument("--text", default="", help="Description")
    parser.add_argument("--contra-account", type=int, help="Contra account (for balancing)")
    args = parser.parse_args()

    if args.interactive or not args.journal:
        interactive_mode()
        return

    entries = [{
        "account": {"accountNumber": args.account},
        "amount": args.amount,
        "text": args.text,
        "date": date.today().isoformat(),
    }]
    if args.contra_account:
        entries.append({
            "account": {"accountNumber": args.contra_account},
            "amount": -args.amount,
            "text": args.text,
            "date": date.today().isoformat(),
        })

    create_voucher(args.journal, entries)


if __name__ == "__main__":
    main()
