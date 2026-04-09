#!/usr/bin/env python3
"""
e-conomic Pipeline — single entry point for everything.

Usage:
  python run.py                # Fetch last 90 days + ingest into SQLite
  python run.py --days 180     # Fetch more history
  python run.py --fetch-only   # Just download JSON files
  python run.py --ingest-only  # Just ingest existing JSON into DB
  python run.py --test         # Test API connection only
  python run.py --explore      # Map your full e-conomic setup
  python run.py --schema       # Build/update schema index for fast lookups
  python run.py --health       # Health check + detect changes
  python run.py --suggest      # Get workflow suggestions based on current state
  python run.py --log          # View recent activity log
"""

import argparse
import sys

import requests
from dotenv import load_dotenv
from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def test_connection() -> bool:
    """Quick check that API tokens work."""
    app_secret = os.environ.get("ECONOMIC_APP_SECRET", "")
    agreement_token = os.environ.get("ECONOMIC_AGREEMENT_TOKEN", "")

    if not app_secret or not agreement_token:
        print("ERROR: Tokens not found. Copy .env.example to .env and fill in your tokens.")
        return False

    print("Testing e-conomic API connection...")
    try:
        r = requests.get(
            "https://restapi.e-conomic.com/self",
            headers={
                "X-AppSecretToken": app_secret,
                "X-AgreementGrantToken": agreement_token,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            company = data.get("company", {}).get("name", "Unknown")
            agreement = data.get("agreementNumber", "?")
            print(f"  Connected to: {company} (agreement {agreement})")
            return True
        else:
            print(f"  Failed: HTTP {r.status_code}")
            print(f"  {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="e-conomic data pipeline")
    parser.add_argument("--days", type=int, default=90, help="Days of journal entries (default: 90)")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch, don't ingest")
    parser.add_argument("--ingest-only", action="store_true", help="Only ingest existing JSON")
    parser.add_argument("--date", default=None, help="Ingest specific date (YYYY-MM-DD)")
    parser.add_argument("--test", action="store_true", help="Test API connection only")
    parser.add_argument("--explore", action="store_true", help="Map your full e-conomic setup (read-only)")
    parser.add_argument("--schema", action="store_true", help="Build/update schema index")
    parser.add_argument("--health", action="store_true", help="Health check and detect changes")
    parser.add_argument("--suggest", action="store_true", help="Suggest workflows based on current state")
    parser.add_argument("--log", action="store_true", help="Show recent activity log")
    parser.add_argument("--dry-run", action="store_true", help="Ingest without writing to DB")
    args = parser.parse_args()

    if args.explore:
        from explore import main as explore_main
        explore_main()
        # Auto-seed knowledge base after first explore
        try:
            from knowledge.loader import rebuild_profile
            rebuild_profile()
            print("\n  Knowledge: business profile updated.")
        except Exception:
            pass
        return

    if args.schema:
        from schema import main as schema_main
        schema_main()
        return

    if args.health:
        from healthcheck import main as health_main
        health_main(fix=True)
        return

    if args.suggest:
        from workflows.suggest import main as suggest_main
        suggest_main()
        return

    if args.log:
        from log import main as log_main
        log_main()
        return

    if args.test:
        ok = test_connection()
        sys.exit(0 if ok else 1)

    if not args.ingest_only:
        # Test connection first
        if not test_connection():
            sys.exit(1)
        print()

        from fetch import main as fetch_main
        result = fetch_main(days=args.days)

        # Log the fetch
        try:
            from log import log_action
            counts = {k: len(v) for k, v in result.items()} if result else {}
            log_action("fetch", f"Fetched data for last {args.days} days", details=counts)
        except Exception:
            pass

    if not args.fetch_only:
        print()
        from ingest import main as ingest_main
        ingest_main(target_date=args.date, dry_run=args.dry_run)

        # Auto-seed knowledge from fetched data
        if not args.dry_run:
            try:
                from knowledge.ingest import ingest as knowledge_ingest
                print()
                knowledge_ingest()
            except Exception:
                pass


if __name__ == "__main__":
    main()
