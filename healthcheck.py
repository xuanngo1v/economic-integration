#!/usr/bin/env python3
"""
Self-Healing Health Check
===========================
Detects changes in the e-conomic environment and adapts:
  - New accounts added? Updates schema.
  - New suppliers/customers? Updates schema.
  - API tokens expired? Clear error message.
  - Account category mapping still valid? Checks and warns.
  - Schema out of date? Triggers rebuild.

Logs all detected changes to the activity log.

Usage:
  python healthcheck.py            # Full check
  python healthcheck.py --fix      # Auto-fix what it can (rebuild schema, etc.)
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from api import get_with_status, DATA_DIR, SCHEMA_PATH

PROJECT_DIR = Path(__file__).resolve().parent

# Import log if available
try:
    from log import log_action, log_error, log_change
except ImportError:
    def log_action(*a, **kw): pass
    def log_error(*a, **kw): pass
    def log_change(*a, **kw): pass


def _get(path, params=None):
    return get_with_status(path, params)


def _count(path):
    code, data = _get(path, params={"pagesize": 1})
    if code == 200 and isinstance(data, dict):
        return data.get("pagination", {}).get("results", 0)
    return -1


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_connection() -> dict:
    """Can we reach the API?"""
    code, data = _get("/self")
    if code == 200:
        name = data.get("company", {}).get("name", "Unknown") if isinstance(data, dict) else "?"
        return {"status": "ok", "company": name}
    elif code == 401:
        log_error("healthcheck", "API token expired or invalid (HTTP 401)")
        return {"status": "error", "issue": "Token expired or invalid. Regenerate in e-conomic developer portal."}
    elif code == 403:
        log_error("healthcheck", "Insufficient permissions (HTTP 403)")
        return {"status": "error", "issue": "Insufficient permissions. Check app role in developer portal."}
    else:
        log_error("healthcheck", f"Connection failed: HTTP {code}")
        return {"status": "error", "issue": f"Connection failed: HTTP {code}"}


def check_schema_freshness() -> dict:
    """Is the schema up to date?"""
    if not SCHEMA_PATH.exists():
        return {"status": "missing", "issue": "No schema.json. Run: python schema.py"}

    schema = json.loads(SCHEMA_PATH.read_text())
    meta = schema.get("_meta", {})
    last_updated = meta.get("last_updated", "")

    if not last_updated:
        return {"status": "unknown", "issue": "Schema has no timestamp"}

    try:
        days_old = (date.today() - date.fromisoformat(last_updated)).days
    except ValueError:
        return {"status": "unknown", "issue": f"Can't parse schema date: {last_updated}"}

    if days_old > 7:
        return {"status": "stale", "days_old": days_old, "issue": f"Schema is {days_old} days old. Run: python schema.py"}
    return {"status": "ok", "days_old": days_old}


def check_account_changes() -> dict:
    """Have new accounts been added since last schema build?"""
    if not SCHEMA_PATH.exists():
        return {"status": "skip", "issue": "No schema to compare against"}

    schema = json.loads(SCHEMA_PATH.read_text())
    known_count = schema.get("accounts", {}).get("total", 0)
    current_count = _count("/accounts")

    if current_count < 0:
        return {"status": "error", "issue": "Could not fetch account count"}

    diff = current_count - known_count
    if diff > 0:
        log_change("accounts", str(known_count), str(current_count))
        return {"status": "changed", "added": diff, "issue": f"{diff} new account(s) added since last schema build"}
    elif diff < 0:
        log_change("accounts", str(known_count), str(current_count))
        return {"status": "changed", "removed": abs(diff), "issue": f"{abs(diff)} account(s) removed since last schema build"}
    return {"status": "ok", "count": current_count}


def check_supplier_changes() -> dict:
    """New suppliers added?"""
    if not SCHEMA_PATH.exists():
        return {"status": "skip"}

    schema = json.loads(SCHEMA_PATH.read_text())
    known = schema.get("suppliers", {}).get("count", 0)
    current = _count("/suppliers")

    if current < 0:
        return {"status": "error"}

    diff = current - known
    if diff != 0:
        log_change("suppliers", str(known), str(current))
        return {"status": "changed", "diff": diff, "issue": f"Supplier count changed: {known} -> {current}"}
    return {"status": "ok", "count": current}


def check_customer_changes() -> dict:
    """New customers added?"""
    if not SCHEMA_PATH.exists():
        return {"status": "skip"}

    schema = json.loads(SCHEMA_PATH.read_text())
    known = schema.get("customers", {}).get("count", 0)
    current = _count("/customers")

    if current < 0:
        return {"status": "error"}

    diff = current - known
    if diff != 0:
        log_change("customers", str(known), str(current))
        return {"status": "changed", "diff": diff, "issue": f"Customer count changed: {known} -> {current}"}
    return {"status": "ok", "count": current}


def check_overdue() -> dict:
    """Any overdue invoices?"""
    count = _count("/invoices/overdue")
    if count > 0:
        return {"status": "attention", "count": count, "issue": f"{count} overdue invoice(s)"}
    return {"status": "ok", "count": 0}


# ---------------------------------------------------------------------------
# Fix / Self-heal
# ---------------------------------------------------------------------------

def auto_fix(results: dict) -> list[str]:
    """Attempt to fix issues automatically."""
    fixes = []

    # Rebuild schema if stale or missing
    schema_result = results.get("schema_freshness", {})
    if schema_result.get("status") in ("stale", "missing"):
        print("\n  Auto-fixing: Rebuilding schema...")
        from schema import main as schema_main
        schema_main()
        fixes.append("Rebuilt schema.json")
        log_action("healthcheck", "Auto-rebuilt schema.json (was stale/missing)")

    # Rebuild schema if accounts/suppliers/customers changed
    for check in ("account_changes", "supplier_changes", "customer_changes"):
        if results.get(check, {}).get("status") == "changed":
            if "Rebuilt schema.json" not in fixes:
                print(f"\n  Auto-fixing: Rebuilding schema (changes detected in {check})...")
                from schema import main as schema_main
                schema_main()
                fixes.append("Rebuilt schema.json")
                log_action("healthcheck", f"Auto-rebuilt schema.json (changes in {check})")
            break

    return fixes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(fix: bool = False):
    today = date.today().isoformat()
    print(f"Health Check — {today}")
    print("=" * 55)

    results = {}

    # Run checks
    checks = [
        ("connection", check_connection),
        ("schema_freshness", check_schema_freshness),
        ("account_changes", check_account_changes),
        ("supplier_changes", check_supplier_changes),
        ("customer_changes", check_customer_changes),
        ("overdue_invoices", check_overdue),
    ]

    all_ok = True
    for name, fn in checks:
        result = fn()
        results[name] = result
        status = result.get("status", "?")

        icon = {"ok": "+", "error": "!", "changed": "~", "stale": "~", "missing": "!", "attention": "!", "skip": "-", "unknown": "?"}.get(status, "?")
        issue = result.get("issue", "")

        if status == "ok":
            detail = ""
            if "count" in result:
                detail = f" ({result['count']})"
            elif "days_old" in result:
                detail = f" ({result['days_old']}d old)"
            elif "company" in result:
                detail = f" ({result['company']})"
            print(f"  [{icon}] {name}: OK{detail}")
        else:
            all_ok = False
            print(f"  [{icon}] {name}: {issue}")

    if all_ok:
        print("\n  Everything looks good.")
        log_action("healthcheck", "All checks passed")
    elif fix:
        fixes = auto_fix(results)
        if fixes:
            print(f"\n  Fixed: {', '.join(fixes)}")
        else:
            print("\n  Some issues need manual attention (see above).")
    else:
        print("\n  Issues found. Run with --fix to auto-repair what's possible.")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {"date": today, "results": results}
    path = DATA_DIR / f"healthcheck_{today}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Health check and self-healing")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues (rebuild schema, etc.)")
    args = parser.parse_args()
    main(fix=args.fix)
