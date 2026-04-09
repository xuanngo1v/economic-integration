#!/usr/bin/env python3
"""
Workflow: Review Corrections (Auto-Capture)
=============================================
Automatically detects when the accountant corrects AI-proposed entries.

Compares what the AI proposed (from activity log) against what was
actually booked in e-conomic. If they differ, captures the correction
as a lesson in the knowledge system.

This is the engine of the learning loop:
  AI proposes → Accountant corrects → This script captures → AI learns

This is READ-ONLY (reads from API and activity log, writes to knowledge).

Usage:
  python workflows/review_corrections.py              # Check recent proposals
  python workflows/review_corrections.py --all        # Check all pending reviews
  python workflows/review_corrections.py --distill    # Also promote lessons to rules
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from api import headers, get, get_all, BASE_URL, DATA_DIR, SCHEMA_PATH

LOG_PATH = DATA_DIR / "activity_log.json"


def get_pending_proposals() -> list[dict]:
    """Get AI-proposed entries that need review from the activity log."""
    if not LOG_PATH.exists():
        return []

    try:
        log = json.loads(LOG_PATH.read_text())
    except (json.JSONDecodeError, Exception):
        return []

    # Find entries marked as requires_review
    pending = [
        e for e in log
        if e.get("requires_review") and e.get("level") == "action"
        and e.get("type") in ("bookkeeping", "write")
    ]
    return pending


def check_voucher_status(journal_num: int, voucher_num: int) -> dict | None:
    """Check if a voucher was booked, modified, or deleted."""
    # Try to find the voucher in the journal's entries
    entries = get_all(f"/journals/{journal_num}/entries", params={
        "pagesize": 100,
        "filter": f"voucherNumber$eq${voucher_num}",
    })
    if entries:
        return {"status": "found", "entries": entries}

    # Check if it was booked (appears in /entries with this voucher number)
    booked = get_all("/entries", params={
        "pagesize": 10,
        "filter": f"voucherNumber$eq${voucher_num}",
    })
    if booked:
        return {"status": "booked", "entries": booked}

    return {"status": "not_found"}


def compare_proposal_to_booked(proposal: dict, booked_entries: list[dict]) -> dict | None:
    """Compare what the AI proposed vs what was actually booked.

    Returns a diff if there are differences, None if they match.
    """
    details = proposal.get("details", {})
    if not details:
        return None

    diff = {}

    # Extract proposed values
    proposed_account = details.get("expense_account", "")
    proposed_amount = details.get("amount")
    proposed_vat = details.get("vat", "")

    # Extract booked values from entries
    for entry in booked_entries:
        acct = entry.get("account", {})
        booked_account = acct.get("accountNumber") if isinstance(acct, dict) else None
        booked_amount = abs(entry.get("amount", 0))

        # Check account number (extract from "2010 (Account Name)" format)
        if proposed_account and booked_account:
            try:
                proposed_num = int(str(proposed_account).split(" ")[0])
                if proposed_num != booked_account:
                    diff["account"] = {"was": proposed_num, "now": booked_account}
            except (ValueError, IndexError):
                pass

        # Check amount
        if proposed_amount and booked_amount:
            if abs(float(proposed_amount) - booked_amount) > 0.01:
                diff["amount"] = {"was": proposed_amount, "now": booked_amount}

    # Check VAT if available
    for entry in booked_entries:
        vat_acct = entry.get("vatAccount", {})
        if vat_acct and proposed_vat:
            booked_vat = vat_acct.get("vatCode", "")
            if booked_vat and booked_vat != proposed_vat:
                diff["vat"] = {"was": proposed_vat, "now": booked_vat}

    return diff if diff else None


def main(check_all: bool = False, also_distill: bool = False):
    today = date.today()
    print(f"Review Corrections — {today.isoformat()}")
    print("=" * 55)

    # Get pending proposals
    proposals = get_pending_proposals()
    if not proposals:
        print("\n  No pending proposals to review.")
        print("  (Proposals are created when the AI makes entries via bookkeeping.py)")
        return

    print(f"\n  Found {len(proposals)} proposal(s) to check.")

    corrections_found = 0
    unchanged = 0
    not_found = 0

    for proposal in proposals:
        details = proposal.get("details", {})
        msg = proposal.get("message", "")
        timestamp = proposal.get("timestamp", "")[:16]

        # Extract journal and voucher from the message
        # Messages look like: "Created supplierInvoice voucher #123 in journal 6: ..."
        journal_num = None
        voucher_num = None

        if "journal" in msg:
            parts = msg.split("journal ")
            if len(parts) > 1:
                try:
                    journal_num = int(parts[1].split(":")[0].split(" ")[0])
                except (ValueError, IndexError):
                    pass

        if "voucher #" in msg:
            parts = msg.split("voucher #")
            if len(parts) > 1:
                try:
                    voucher_num = int(parts[1].split(" ")[0].split(":")[0])
                except (ValueError, IndexError):
                    pass

        print(f"\n  [{timestamp}] {msg[:60]}...")

        if not journal_num or not voucher_num:
            print(f"    Could not extract journal/voucher numbers. Skipping.")
            not_found += 1
            continue

        # Check status in e-conomic
        status = check_voucher_status(journal_num, voucher_num)
        if not status or status["status"] == "not_found":
            print(f"    Voucher #{voucher_num} not found — may have been deleted or not yet booked.")
            not_found += 1
            continue

        # Compare
        diff = compare_proposal_to_booked(proposal, status.get("entries", []))

        if diff:
            corrections_found += 1
            print(f"    CORRECTION DETECTED:")
            for field, change in diff.items():
                print(f"      {field}: {change['was']} → {change['now']}")

            # Capture as a lesson
            try:
                from knowledge.loader import add_lesson
                context = {
                    "task_type": "supplier_invoice" if "supplier" in msg.lower() else "expense",
                    "supplier": details.get("supplier", ""),
                    "description": details.get("description", ""),
                    "journal": journal_num,
                }

                original = {}
                corrected = {}
                for field, change in diff.items():
                    original[field] = change["was"]
                    corrected[field] = change["now"]

                lesson = add_lesson(original, corrected, context)
                print(f"    → Saved as {lesson['id']}")
            except Exception as e:
                print(f"    → Could not save lesson: {e}")
        else:
            unchanged += 1
            print(f"    Booked as proposed. No corrections.")

    # Summary
    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  Checked:     {len(proposals)}")
    print(f"  Corrections: {corrections_found}")
    print(f"  Unchanged:   {unchanged}")
    print(f"  Not found:   {not_found}")

    if corrections_found:
        print(f"\n  {corrections_found} new lesson(s) captured.")
        print(f"  The AI will use these next time it proposes similar entries.")

        if also_distill:
            print(f"\n  Running distillation...")
            from knowledge.loader import distill_rules
            distill_rules()
    else:
        print(f"\n  No corrections found. The AI's proposals matched what was booked.")

    # Log
    try:
        from log import log_action
        log_action("review", f"Reviewed {len(proposals)} proposals: {corrections_found} corrections, {unchanged} unchanged",
                   details={"corrections": corrections_found, "unchanged": unchanged, "not_found": not_found})
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Review accountant corrections and capture lessons")
    parser.add_argument("--all", action="store_true", help="Check all pending reviews")
    parser.add_argument("--distill", action="store_true", help="Also promote lessons to rules")
    args = parser.parse_args()
    main(check_all=args.all, also_distill=args.distill)
