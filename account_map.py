"""
Account Category Mapping
==========================
Maps e-conomic account numbers to P&L categories.

This file is the SINGLE SOURCE OF TRUTH for account categorization.
All scripts import from here instead of having their own mapping.

The mapping should be auto-detected from YOUR chart of accounts.
Run explore.py first, then adjust the ranges below to match your setup.

If the accountant changes the chart of accounts, run:

    python account_map.py --detect

to see the current structure and update accordingly.

Current mapping: Standard chart of accounts (default).
Adjust the ranges below to match YOUR accountant's setup.
"""

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------
# This is loaded by all workflows. Edit here, changes apply everywhere.
#
# DEFAULT: Standard chart of accounts ranges.
# Your accountant may use different ranges — run:
#   python account_map.py --detect
# to see your actual structure and update these ranges.
#
# Common variations:
#   - Some accountants put COGS in the 2xxx range instead of 3xxx
#   - Some put labor in the 2xxx range instead of 4xxx
#   - Platform fees may be under sales costs or operating expenses
#   - Always check with: python explore.py --section accounts

def map_account_category(account_number) -> str:
    """Map account number to P&L category based on YOUR chart of accounts.

    Edit the ranges below to match your accountant's chart of accounts.
    """
    if account_number is None:
        return "other"
    n = int(account_number)

    # Revenue
    if 1000 <= n <= 1999:
        return "revenue"

    # Cost of goods (COGS)
    if 2000 <= n <= 2999:
        return "cogs"

    # Labor / staff costs
    if 3000 <= n <= 3999:
        return "labor"

    # Premises (rent, utilities, cleaning, maintenance)
    if 4000 <= n <= 4299:
        return "premises"

    # Transport
    if 4300 <= n <= 4399:
        return "transport"

    # Sales costs / platform fees
    if 4400 <= n <= 4599:
        return "platform_fees"

    # Other operating
    if 4600 <= n <= 4699:
        return "other_ops"

    # Administration (IT, phone, accounting, insurance)
    if 4700 <= n <= 4999:
        return "admin"

    # Depreciation
    if 5000 <= n <= 5499:
        return "depreciation"

    # Financial income
    if 5500 <= n <= 5599:
        return "financial_income"

    # Financial expense
    if 5600 <= n <= 5999:
        return "financial_expense"

    # Tax
    if 6000 <= n <= 6999:
        return "tax"

    # Balance sheet items (not P&L)
    if n >= 7000:
        return "balance_sheet"

    return "other"


# Category labels
CATEGORY_LABELS = {
    "revenue": "Revenue",
    "cogs": "Cost of Goods",
    "labor": "Staff Costs",
    "premises": "Premises",
    "transport": "Transport",
    "platform_fees": "Platform Fees",
    "other_ops": "Other Operating",
    "admin": "Administration",
    "depreciation": "Depreciation",
    "financial_income": "Financial Income",
    "financial_expense": "Financial Expense",
    "tax": "Tax",
    "balance_sheet": "Balance (not P&L)",
    "other": "Other",
}


# P&L line order (for reports)
PL_ORDER = [
    "revenue",
    "cogs",
    "labor",
    "premises",
    "transport",
    "platform_fees",
    "admin",
    "other_ops",
    "depreciation",
    "financial_income",
    "financial_expense",
    "tax",
]


# ---------------------------------------------------------------------------
# Auto-detection (run this if chart of accounts changes)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Account mapping utility")
    parser.add_argument("--detect", action="store_true", help="Detect mapping from schema")
    parser.add_argument("--test", help="Test: map a single account number", type=int)
    parser.add_argument("--show", action="store_true", help="Show current mapping")
    args = parser.parse_args()

    if args.test:
        cat = map_account_category(args.test)
        label = CATEGORY_LABELS.get(cat, cat)
        print(f"  Account {args.test} -> {cat} ({label})")

    elif args.show:
        print("Current account mapping:")
        print()
        for cat in PL_ORDER:
            label = CATEGORY_LABELS.get(cat, cat)
            print(f"  {cat:<20} {label}")

    elif args.detect:
        import json
        from pathlib import Path
        schema_path = Path(__file__).parent / "data" / "schema.json"
        if not schema_path.exists():
            print("No schema.json found. Run: python schema.py")
        else:
            schema = json.loads(schema_path.read_text())
            accounts = schema.get("accounts", {}).get("lookup", {})
            print(f"Loaded {len(accounts)} accounts from schema.json\n")

            # Show headings to understand structure
            headings = [(int(k), v) for k, v in accounts.items() if v.get("type") == "heading"]
            headings.sort()
            print("Account headings (your chart of accounts structure):")
            for num, info in headings:
                print(f"  {num:>6}  {info['name']}")

            print("\nCurrent mapping applied to all P&L accounts:")
            pl_accounts = [(int(k), v) for k, v in accounts.items()
                          if v.get("type") == "profitAndLoss"]
            pl_accounts.sort()
            for num, info in pl_accounts:
                cat = map_account_category(num)
                print(f"  {num:>6}  {info['name']:<45} -> {cat}")

            print("\n  If the mapping looks wrong, edit the ranges in this file.")
            print("  Then re-run your workflows to see updated P&L reports.")
    else:
        parser.print_help()
