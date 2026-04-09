"""Tests for account_map.py — the single source of truth for categorization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from account_map import map_account_category, CATEGORY_LABELS, PL_ORDER


class TestMapAccountCategory:
    def test_revenue(self):
        assert map_account_category(1000) == "revenue"
        assert map_account_category(1500) == "revenue"
        assert map_account_category(1999) == "revenue"

    def test_cogs(self):
        assert map_account_category(2000) == "cogs"
        assert map_account_category(2500) == "cogs"
        assert map_account_category(2999) == "cogs"

    def test_labor(self):
        assert map_account_category(3000) == "labor"
        assert map_account_category(3999) == "labor"

    def test_premises(self):
        assert map_account_category(4000) == "premises"
        assert map_account_category(4299) == "premises"

    def test_transport(self):
        assert map_account_category(4300) == "transport"
        assert map_account_category(4399) == "transport"

    def test_platform_fees(self):
        assert map_account_category(4400) == "platform_fees"
        assert map_account_category(4599) == "platform_fees"

    def test_other_ops(self):
        assert map_account_category(4600) == "other_ops"
        assert map_account_category(4699) == "other_ops"

    def test_admin(self):
        assert map_account_category(4700) == "admin"
        assert map_account_category(4999) == "admin"

    def test_depreciation(self):
        assert map_account_category(5000) == "depreciation"
        assert map_account_category(5499) == "depreciation"

    def test_financial_income(self):
        assert map_account_category(5500) == "financial_income"
        assert map_account_category(5599) == "financial_income"

    def test_financial_expense(self):
        assert map_account_category(5600) == "financial_expense"
        assert map_account_category(5999) == "financial_expense"

    def test_tax(self):
        assert map_account_category(6000) == "tax"
        assert map_account_category(6999) == "tax"

    def test_balance_sheet(self):
        assert map_account_category(7000) == "balance_sheet"
        assert map_account_category(8000) == "balance_sheet"
        assert map_account_category(9999) == "balance_sheet"

    def test_none_returns_other(self):
        assert map_account_category(None) == "other"

    def test_low_numbers_return_other(self):
        assert map_account_category(0) == "other"
        assert map_account_category(999) == "other"

    def test_boundaries(self):
        """Test that boundaries between categories are correct."""
        assert map_account_category(1999) == "revenue"
        assert map_account_category(2000) == "cogs"
        assert map_account_category(2999) == "cogs"
        assert map_account_category(3000) == "labor"
        assert map_account_category(4299) == "premises"
        assert map_account_category(4300) == "transport"
        assert map_account_category(4399) == "transport"
        assert map_account_category(4400) == "platform_fees"
        assert map_account_category(4599) == "platform_fees"
        assert map_account_category(4600) == "other_ops"
        assert map_account_category(4699) == "other_ops"
        assert map_account_category(4700) == "admin"
        assert map_account_category(6999) == "tax"
        assert map_account_category(7000) == "balance_sheet"

    def test_string_number(self):
        """Account numbers might come as strings from JSON."""
        assert map_account_category("3000") == "labor"
        assert map_account_category("1500") == "revenue"


class TestCategoryLabels:
    def test_all_pl_order_categories_have_labels(self):
        for cat in PL_ORDER:
            assert cat in CATEGORY_LABELS, f"Missing label for {cat}"

    def test_labels_are_strings(self):
        for cat, label in CATEGORY_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0

    def test_pl_order_has_no_duplicates(self):
        assert len(PL_ORDER) == len(set(PL_ORDER))
