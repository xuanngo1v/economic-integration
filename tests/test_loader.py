"""Tests for knowledge/loader.py — the knowledge system."""

import json
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture
def temp_knowledge(tmp_path):
    """Create a temporary knowledge directory for testing."""
    # Copy the structure
    static_dir = tmp_path / "static"
    business_dir = tmp_path / "business"
    lessons_dir = tmp_path / "lessons"
    static_dir.mkdir()
    business_dir.mkdir()
    lessons_dir.mkdir()

    # Create minimal static files
    (static_dir / "double_entry.md").write_text("# Double Entry\nTest content.")
    (static_dir / "common_transactions.md").write_text("# Common Transactions\nTest.")
    (static_dir / "vat_rules.md").write_text("# VAT Rules\nTest.")
    (static_dir / "chart_of_accounts.md").write_text("# Chart of Accounts\nTest.")
    (static_dir / "compliance.md").write_text("# Compliance\nTest.")

    # Create business files
    (business_dir / "profile.md").write_text("# Business Profile\nTest company.")
    (business_dir / "preferences.md").write_text("# Preferences\n")

    # Create empty lessons/rules
    (lessons_dir / "lessons.json").write_text("[]")
    (lessons_dir / "rules.json").write_text("[]")

    # Create index and log
    (tmp_path / "index.md").write_text("# Index\n")
    (tmp_path / "log.md").write_text("# Log\n")

    return tmp_path


@pytest.fixture
def patch_loader(temp_knowledge, monkeypatch):
    """Patch loader.py to use temp directory."""
    from knowledge import loader
    monkeypatch.setattr(loader, "KNOWLEDGE_DIR", temp_knowledge)
    monkeypatch.setattr(loader, "STATIC_DIR", temp_knowledge / "static")
    monkeypatch.setattr(loader, "BUSINESS_DIR", temp_knowledge / "business")
    monkeypatch.setattr(loader, "LESSONS_DIR", temp_knowledge / "lessons")
    monkeypatch.setattr(loader, "LESSONS_PATH", temp_knowledge / "lessons" / "lessons.json")
    monkeypatch.setattr(loader, "RULES_PATH", temp_knowledge / "lessons" / "rules.json")
    monkeypatch.setattr(loader, "INDEX_PATH", temp_knowledge / "index.md")
    monkeypatch.setattr(loader, "LOG_PATH", temp_knowledge / "log.md")
    return loader


class TestLoadKnowledge:
    def test_loads_static_for_supplier_invoice(self, patch_loader):
        k = patch_loader.load_knowledge("supplier_invoice")
        assert len(k["static"]) == 2  # common_transactions + vat_rules
        assert "Common Transactions" in k["static"][0]

    def test_loads_static_for_explanation(self, patch_loader):
        k = patch_loader.load_knowledge("explanation")
        assert len(k["static"]) == 2  # double_entry + chart_of_accounts

    def test_loads_profile(self, patch_loader):
        k = patch_loader.load_knowledge("supplier_invoice")
        assert "Business Profile" in k["profile"]

    def test_loads_preferences(self, patch_loader):
        k = patch_loader.load_knowledge("supplier_invoice")
        assert "Preferences" in k["preferences"]

    def test_empty_rules_and_lessons(self, patch_loader):
        k = patch_loader.load_knowledge("supplier_invoice")
        assert k["rules"] == []
        assert k["lessons"] == []

    def test_unknown_task_type_returns_empty_static(self, patch_loader):
        k = patch_loader.load_knowledge("unknown_task")
        assert k["static"] == []


class TestAddLesson:
    def test_add_lesson_creates_entry(self, patch_loader):
        lesson = patch_loader.add_lesson(
            original={"account": 2000},
            corrected={"account": 2010},
            context={"task_type": "supplier_invoice", "supplier": "Test"},
            reason="Wrong account"
        )
        assert lesson["id"] == "lesson_001"
        assert lesson["diff"] == {"account": {"was": 2000, "now": 2010}}
        assert lesson["reason"] == "Wrong account"

    def test_add_multiple_lessons(self, patch_loader):
        patch_loader.add_lesson({"account": 2000}, {"account": 2010}, {"task_type": "supplier_invoice"})
        patch_loader.add_lesson({"vat": "I25"}, {"vat": "U25"}, {"task_type": "expense"})

        lessons = json.loads((patch_loader.LESSONS_PATH).read_text())
        assert len(lessons) == 2
        assert lessons[0]["id"] == "lesson_001"
        assert lessons[1]["id"] == "lesson_002"

    def test_lesson_appears_in_load_knowledge(self, patch_loader):
        patch_loader.add_lesson(
            {"account": 2000}, {"account": 2010},
            {"task_type": "supplier_invoice", "supplier": "Test"}
        )
        k = patch_loader.load_knowledge("supplier_invoice", context={"supplier": "Test"})
        assert len(k["lessons"]) == 1


class TestDistillRules:
    def test_no_lessons_no_rules(self, patch_loader, capsys):
        patch_loader.distill_rules()
        out = capsys.readouterr().out
        assert "No lessons" in out

    def test_below_threshold_no_promotion(self, patch_loader, capsys):
        # Add 2 similar lessons (threshold is 3)
        for _ in range(2):
            patch_loader.add_lesson({"account": 2000}, {"account": 2010}, {"task_type": "supplier_invoice"})
        patch_loader.distill_rules(threshold=3)
        rules = json.loads(patch_loader.RULES_PATH.read_text())
        assert len(rules) == 0

    def test_at_threshold_promotes(self, patch_loader):
        # Add 3 identical corrections
        for _ in range(3):
            patch_loader.add_lesson({"account": 2000}, {"account": 2010}, {"task_type": "supplier_invoice"})
        patch_loader.distill_rules(threshold=3)
        rules = json.loads(patch_loader.RULES_PATH.read_text())
        assert len(rules) == 1
        assert rules[0]["count"] == 3

    def test_rule_appears_in_load_knowledge(self, patch_loader):
        for _ in range(3):
            patch_loader.add_lesson({"account": 2000}, {"account": 2010}, {"task_type": "supplier_invoice"})
        patch_loader.distill_rules(threshold=3)

        k = patch_loader.load_knowledge("supplier_invoice")
        assert len(k["rules"]) == 1


class TestAddPreference:
    def test_add_preference(self, patch_loader):
        patch_loader.add_preference("journal_selection", "Use journal 6 for suppliers", "user")
        content = (patch_loader.BUSINESS_DIR / "preferences.md").read_text()
        assert "Use journal 6 for suppliers" in content
        assert "journal_selection" in content


class TestLint:
    def test_clean_knowledge_passes(self, patch_loader):
        issues = patch_loader.lint()
        assert len(issues) == 0

    def test_missing_static_file_detected(self, patch_loader):
        (patch_loader.STATIC_DIR / "double_entry.md").unlink()
        issues = patch_loader.lint()
        assert any("double_entry.md" in i for i in issues)

    def test_lessons_without_reason_detected(self, patch_loader):
        patch_loader.add_lesson({"a": 1}, {"a": 2}, {"task_type": "test"})
        issues = patch_loader.lint()
        assert any("missing a reason" in i for i in issues)
