#!/usr/bin/env python3
"""
Activity Log
==============
Tracks everything the agent and user have done — a persistent history
so you always know what happened, when, and what changed.

The log is append-only. Nothing is ever deleted.

Entries are stored in data/activity_log.json.

Usage from other scripts:
  from log import log_action, log_error, log_note, get_recent

  log_action("fetch", "Fetched 145 invoices and 89 journal entries")
  log_action("workflow", "Ran P&L report for last 3 months", details={"revenue": 450000})
  log_action("write", "Created draft invoice #1234 for Customer X", requires_review=True)
  log_error("fetch", "HTTP 401 — token expired")
  log_note("User wants weekly P&L reports every Monday")

Usage from CLI:
  python log.py                    # Show last 20 entries
  python log.py --all              # Show everything
  python log.py --type workflow    # Filter by type
  python log.py --since 2026-04-01 # Filter by date
  python log.py --add "Manual note about something"
"""

import argparse
import json
from datetime import datetime, date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
LOG_PATH = DATA_DIR / "activity_log.json"


def _load_log() -> list[dict]:
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text())
        except (json.JSONDecodeError, Exception):
            return []
    return []


def _save_log(entries: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False, default=str)


def _append(entry: dict):
    entries = _load_log()
    entries.append(entry)
    _save_log(entries)


# ---------------------------------------------------------------------------
# Public API — use these from other scripts
# ---------------------------------------------------------------------------

def log_action(action_type: str, message: str, details: dict | None = None, requires_review: bool = False):
    """Log a completed action."""
    _append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": "action",
        "type": action_type,
        "message": message,
        "details": details,
        "requires_review": requires_review,
    })


def log_error(action_type: str, message: str, details: dict | None = None):
    """Log an error."""
    _append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": "error",
        "type": action_type,
        "message": message,
        "details": details,
    })


def log_note(message: str):
    """Log a freeform note (user preference, decision, etc.)."""
    _append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": "note",
        "type": "note",
        "message": message,
    })


def log_change(what: str, before: str | None, after: str | None, source: str = "detected"):
    """Log a detected change in the environment (self-healing)."""
    _append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": "change",
        "type": "environment",
        "message": f"Change detected: {what}",
        "details": {"what": what, "before": before, "after": after, "source": source},
    })


def get_recent(n: int = 20, entry_type: str | None = None, since: str | None = None) -> list[dict]:
    """Get recent log entries with optional filters."""
    entries = _load_log()
    if entry_type:
        entries = [e for e in entries if e.get("type") == entry_type]
    if since:
        entries = [e for e in entries if e.get("timestamp", "") >= since]
    return entries[-n:]


def get_pending_reviews() -> list[dict]:
    """Get actions that were flagged as needing review."""
    entries = _load_log()
    return [e for e in entries if e.get("requires_review")]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_entries(entries: list[dict]):
    if not entries:
        print("  No entries found.")
        return

    for e in entries:
        ts = e.get("timestamp", "?")[:16]
        level = e.get("level", "?")
        etype = e.get("type", "")
        msg = e.get("message", "")

        icon = {"action": " ", "error": "!", "note": "#", "change": "~"}.get(level, "?")
        review = " [NEEDS REVIEW]" if e.get("requires_review") else ""

        print(f"  {ts}  {icon} [{etype}] {msg}{review}")

        if e.get("details") and isinstance(e["details"], dict):
            for k, v in e["details"].items():
                print(f"               {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="View activity log")
    parser.add_argument("--all", action="store_true", help="Show all entries")
    parser.add_argument("-n", type=int, default=20, help="Number of entries (default: 20)")
    parser.add_argument("--type", dest="entry_type", help="Filter by type (fetch, workflow, write, note, etc.)")
    parser.add_argument("--since", help="Show entries since date (YYYY-MM-DD)")
    parser.add_argument("--add", help="Add a manual note")
    parser.add_argument("--pending", action="store_true", help="Show actions needing review")
    args = parser.parse_args()

    if args.add:
        log_note(args.add)
        print(f"  Note added: {args.add}")
        return

    if args.pending:
        print("Pending Reviews:")
        print_entries(get_pending_reviews())
        return

    entries = _load_log()

    if args.entry_type:
        entries = [e for e in entries if e.get("type") == args.entry_type]
    if args.since:
        entries = [e for e in entries if e.get("timestamp", "") >= args.since]

    if not args.all:
        entries = entries[-args.n:]

    total = len(_load_log())
    showing = len(entries)
    print(f"Activity Log — {showing} of {total} entries")
    print("=" * 55)
    print_entries(entries)


if __name__ == "__main__":
    main()
