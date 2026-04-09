#!/usr/bin/env python3
"""
Shared API Module
===================
Common functions for talking to the e-conomic REST API.

All scripts import from here instead of defining their own
_headers(), _get(), _get_all() functions.

Usage:
    from api import headers, get, get_all, count, BASE_URL, DATA_DIR
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

BASE_URL = "https://restapi.e-conomic.com"
DATA_DIR = PROJECT_DIR / "data"
SCHEMA_PATH = DATA_DIR / "schema.json"


def headers() -> dict:
    """Build auth headers for the e-conomic API."""
    app_secret = os.environ.get("ECONOMIC_APP_SECRET", "")
    agreement_token = os.environ.get("ECONOMIC_AGREEMENT_TOKEN", "")
    if not app_secret or not agreement_token:
        print("ERROR: ECONOMIC_APP_SECRET and ECONOMIC_AGREEMENT_TOKEN required in .env")
        print("       Copy .env.example to .env and fill in your tokens.")
        sys.exit(1)
    return {
        "X-AppSecretToken": app_secret,
        "X-AgreementGrantToken": agreement_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get(path: str, params: dict | None = None) -> dict | list | None:
    """Safe GET — returns None on error instead of crashing."""
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers(), params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def get_all(path: str, params: dict | None = None) -> list[dict]:
    """Paginated GET — follows nextPage, returns all collected items."""
    hdrs = headers()
    items: list[dict] = []
    url: str | None = f"{BASE_URL}{path}"
    while url:
        r = requests.get(url, headers=hdrs, params=params, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        items.extend(data.get("collection", []))
        params = None  # After first request, params are in nextPage URL
        url = (data.get("pagination") or {}).get("nextPage")
    return items


def count(path: str) -> int:
    """Quick count of items at an endpoint (single page fetch)."""
    data = get(path, params={"pagesize": 1})
    if data and isinstance(data, dict) and "pagination" in data:
        return data["pagination"].get("results", 0)
    return 0


def get_with_status(path: str, params: dict | None = None) -> tuple[int, dict | str]:
    """GET that returns (status_code, data) — used by healthcheck."""
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers(), params=params, timeout=15)
        return r.status_code, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return 0, str(e)
