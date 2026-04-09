#!/usr/bin/env python3
"""
Knowledge Loader
==================
Single entry point for the knowledge system. All workflows import from here.

Implements the LLM Wiki pattern: persistent, compounding knowledge that the
AI reads before acting and updates after learning.

Usage from workflows:
    from knowledge.loader import load_knowledge, add_lesson, add_preference

    # Before creating an entry
    k = load_knowledge("supplier_invoice", context={"supplier": "Supplier X"})
    # k["rules"] → matching rules from past corrections
    # k["lessons"] → individual corrections for similar entries
    # k["static"] → relevant bookkeeping knowledge

    # After accountant corrects an entry
    add_lesson(
        original={"account": 2000, "vat": "I25"},
        corrected={"account": 2010, "vat": "I25"},
        context={"supplier": "Supplier X", "description": "Goods delivery"},
        reason="Food purchases go to 2010, not 2000"
    )

Usage from CLI:
    python knowledge/loader.py --lint              # Health check
    python knowledge/loader.py --distill           # Promote lessons to rules
    python knowledge/loader.py --rebuild-profile   # Regenerate business profile
    python knowledge/loader.py --show              # Show knowledge summary
"""

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = KNOWLEDGE_DIR / "static"
BUSINESS_DIR = KNOWLEDGE_DIR / "business"
LESSONS_DIR = KNOWLEDGE_DIR / "lessons"
PROJECT_DIR = KNOWLEDGE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
INDEX_PATH = KNOWLEDGE_DIR / "index.md"
LOG_PATH = KNOWLEDGE_DIR / "log.md"
LESSONS_PATH = LESSONS_DIR / "lessons.json"
RULES_PATH = LESSONS_DIR / "rules.json"


# ---------------------------------------------------------------------------
# Task-to-knowledge mapping
# ---------------------------------------------------------------------------

TASK_KNOWLEDGE = {
    "supplier_invoice": ["common_transactions.md", "vat_rules.md"],
    "expense": ["common_transactions.md", "vat_rules.md"],
    "invoice": ["common_transactions.md", "vat_rules.md"],
    "journal_entry": ["common_transactions.md", "double_entry.md"],
    "explanation": ["double_entry.md", "chart_of_accounts.md"],
    "report": ["chart_of_accounts.md"],
    "compliance": ["compliance.md", "vat_rules.md"],
}


# ---------------------------------------------------------------------------
# Core: Load knowledge
# ---------------------------------------------------------------------------

def load_knowledge(task_type: str, context: dict | None = None) -> dict:
    """Load all relevant knowledge for a task.

    Args:
        task_type: "supplier_invoice", "expense", "invoice", "explanation", "report", "compliance"
        context: optional dict with supplier, amount, description, account, etc.

    Returns:
        {
            "static": list[str],       # Relevant markdown content
            "profile": str,            # Business profile content
            "preferences": str,        # Preferences content
            "rules": list[dict],       # Matching rules
            "lessons": list[dict],     # Matching lessons
        }
    """
    result = {
        "static": [],
        "profile": "",
        "preferences": "",
        "rules": [],
        "lessons": [],
    }

    # Load relevant static knowledge
    files = TASK_KNOWLEDGE.get(task_type, [])
    for filename in files:
        path = STATIC_DIR / filename
        if path.exists():
            result["static"].append(path.read_text())

    # Load business knowledge
    profile_path = BUSINESS_DIR / "profile.md"
    if profile_path.exists():
        result["profile"] = profile_path.read_text()

    prefs_path = BUSINESS_DIR / "preferences.md"
    if prefs_path.exists():
        result["preferences"] = prefs_path.read_text()

    # Load matching rules
    result["rules"] = _get_matching_rules(task_type, context)

    # Load matching lessons
    result["lessons"] = _get_matching_lessons(task_type, context)

    return result


def _get_matching_rules(task_type: str, context: dict | None = None) -> list[dict]:
    """Get rules that apply to this task type and context."""
    if not RULES_PATH.exists():
        return []
    try:
        rules = json.loads(RULES_PATH.read_text())
    except (json.JSONDecodeError, Exception):
        return []

    matches = []
    for rule in rules:
        if rule.get("applies_to") == task_type or rule.get("applies_to") == "all":
            # If rule has a match condition, check context
            match_cond = rule.get("match", {})
            if match_cond and context:
                if all(context.get(k) == v for k, v in match_cond.items()):
                    matches.append(rule)
            elif not match_cond:
                matches.append(rule)
    return matches


def _get_matching_lessons(task_type: str, context: dict | None = None) -> list[dict]:
    """Get lessons relevant to this task type."""
    if not LESSONS_PATH.exists():
        return []
    try:
        lessons = json.loads(LESSONS_PATH.read_text())
    except (json.JSONDecodeError, Exception):
        return []

    matches = []
    for lesson in lessons:
        if lesson.get("trigger") == task_type:
            # Optionally filter by context similarity
            if context and lesson.get("context"):
                # Same supplier or same account = relevant
                lc = lesson["context"]
                if (context.get("supplier") and lc.get("supplier") == context["supplier"]) or \
                   (context.get("account") and lc.get("account") == context["account"]):
                    matches.append(lesson)
                    continue
            matches.append(lesson)
    return matches


# ---------------------------------------------------------------------------
# Learning: Add lessons
# ---------------------------------------------------------------------------

def add_lesson(original: dict, corrected: dict, context: dict, reason: str | None = None):
    """Record a correction as a lesson.

    Args:
        original: what the AI proposed (e.g. {"account": 2000, "vat": "I25"})
        corrected: what the accountant changed it to
        context: supplier name, description, amount, etc.
        reason: why the correction was made (optional, can be filled later)
    """
    lessons = []
    if LESSONS_PATH.exists():
        try:
            lessons = json.loads(LESSONS_PATH.read_text())
        except (json.JSONDecodeError, Exception):
            lessons = []

    # Build the diff
    diff = {}
    for key in set(list(original.keys()) + list(corrected.keys())):
        if original.get(key) != corrected.get(key):
            diff[key] = {"was": original.get(key), "now": corrected.get(key)}

    lesson = {
        "id": f"lesson_{len(lessons) + 1:03d}",
        "date": date.today().isoformat(),
        "trigger": context.get("task_type", "unknown"),
        "original": original,
        "corrected": corrected,
        "diff": diff,
        "context": context,
        "reason": reason,
    }

    lessons.append(lesson)
    LESSONS_PATH.write_text(json.dumps(lessons, indent=2, ensure_ascii=False, default=str))

    # Log it
    _log(f"correction | Lesson {lesson['id']}: {diff}")

    return lesson


# ---------------------------------------------------------------------------
# Learning: Add preferences
# ---------------------------------------------------------------------------

def add_preference(category: str, rule: str, source: str = "user"):
    """Record a user or accountant preference.

    Args:
        category: "journal_selection", "account_selection", "vat_code", etc.
        rule: the preference in plain language
        source: "user", "accountant", "detected"
    """
    prefs_path = BUSINESS_DIR / "preferences.md"
    content = prefs_path.read_text() if prefs_path.exists() else "# Preferences\n"

    entry = f"\n## [{date.today().isoformat()}] {category} ({source})\n{rule}\n"
    content += entry
    prefs_path.write_text(content)

    _log(f"preference | {category}: {rule} (source: {source})")


# ---------------------------------------------------------------------------
# Distill: Promote lessons to rules
# ---------------------------------------------------------------------------

def distill_rules(threshold: int = 3):
    """Promote repeated correction patterns into stable rules.

    When the same correction appears `threshold`+ times, it becomes a rule.
    """
    if not LESSONS_PATH.exists():
        print("  No lessons to distill.")
        return

    lessons = json.loads(LESSONS_PATH.read_text())
    if not lessons:
        print("  No lessons to distill.")
        return

    # Load existing rules
    rules = []
    if RULES_PATH.exists():
        try:
            rules = json.loads(RULES_PATH.read_text())
        except (json.JSONDecodeError, Exception):
            rules = []

    existing_rule_ids = {r["id"] for r in rules}

    # Group lessons by correction pattern
    patterns = Counter()
    pattern_lessons = {}
    for lesson in lessons:
        # Create a pattern key from the diff
        diff = lesson.get("diff", {})
        if not diff:
            continue
        pattern_key = json.dumps(diff, sort_keys=True)
        patterns[pattern_key] += 1

        if pattern_key not in pattern_lessons:
            pattern_lessons[pattern_key] = []
        pattern_lessons[pattern_key].append(lesson)

    # Promote patterns above threshold
    new_rules = 0
    for pattern_key, count in patterns.items():
        if count >= threshold:
            lesson_ids = [l["id"] for l in pattern_lessons[pattern_key]]
            rule_id = f"rule_{len(rules) + new_rules + 1:03d}"

            if any(set(r.get("based_on_lessons", [])) == set(lesson_ids) for r in rules):
                continue  # Already a rule for this pattern

            diff = json.loads(pattern_key)
            sample = pattern_lessons[pattern_key][0]

            rule = {
                "id": rule_id,
                "created": date.today().isoformat(),
                "based_on_lessons": lesson_ids,
                "count": count,
                "rule": f"Correction pattern seen {count} times: {diff}",
                "applies_to": sample.get("trigger", "unknown"),
                "diff": diff,
            }
            rules.append(rule)
            new_rules += 1
            print(f"  Promoted: {rule_id} — {diff} (seen {count}x)")

    if new_rules:
        RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False, default=str))
        _log(f"distill | Promoted {new_rules} new rule(s) from {len(lessons)} lessons")
        print(f"\n  {new_rules} new rule(s) created. Total rules: {len(rules)}")
    else:
        print(f"  No patterns found above threshold ({threshold}). {len(lessons)} lessons checked.")


# ---------------------------------------------------------------------------
# Profile: Rebuild from explorer data
# ---------------------------------------------------------------------------

def rebuild_profile():
    """Regenerate business/profile.md from schema.json and explorer report."""
    schema_path = DATA_DIR / "schema.json"
    if not schema_path.exists():
        print("  No schema.json found. Run: python schema.py")
        return

    schema = json.loads(schema_path.read_text())
    company = schema.get("company", {})
    accounts = schema.get("accounts", {})
    journals = schema.get("journals", {})
    suppliers = schema.get("suppliers", {})
    customers = schema.get("customers", {})
    counts = schema.get("counts", {})
    vat = schema.get("vat", {})

    lines = [
        "# Business Profile",
        "",
        f"Auto-generated on {date.today().isoformat()} from `schema.json`.",
        f"Rebuild with: `python knowledge/loader.py --rebuild-profile`",
        "",
        "## Company",
        "",
        f"- **Name:** {company.get('name', 'Unknown')}",
        f"- **Agreement:** {company.get('agreement', '?')}",
        f"- **Base currency:** {company.get('base_currency', '?')}",
        "",
        "## Account Structure",
        "",
        f"- **Total accounts:** {accounts.get('total', '?')}",
        "",
        "Category ranges (from `account_map.py`):",
        "",
    ]

    # Import account_map if available
    try:
        import sys
        sys.path.insert(0, str(PROJECT_DIR))
        from account_map import CATEGORY_LABELS, PL_ORDER
        for cat in PL_ORDER:
            label = CATEGORY_LABELS.get(cat, cat)
            lines.append(f"- **{label}** — `{cat}`")
    except ImportError:
        lines.append("- (Run from project root to see category details)")

    lines.extend([
        "",
        "## Journals",
        "",
    ])
    for j in journals.get("journals", []):
        restriction = j.get("restriction", "all types")
        lines.append(f"- **Journal {j.get('number', '?')}:** {j.get('name', '?')} ({restriction})")

    lines.extend([
        "",
        "## Counts",
        "",
        f"- Suppliers: {suppliers.get('count', counts.get('suppliers', '?'))}",
        f"- Customers: {customers.get('count', counts.get('customers', '?'))}",
        f"- Booked invoices: {counts.get('invoices_booked', '?')}",
        f"- Unpaid invoices: {counts.get('invoices_unpaid', '?')}",
        f"- Overdue invoices: {counts.get('invoices_overdue', '?')}",
    ])

    if vat.get("accounts"):
        lines.extend([
            "",
            "## VAT Codes",
            "",
        ])
        for v in vat["accounts"][:10]:
            rate = f"{v.get('rate', '?')}%" if v.get('rate') is not None else ""
            lines.append(f"- **{v.get('code', '?')}** — {v.get('name', '')} {rate}")

    profile_path = BUSINESS_DIR / "profile.md"
    profile_path.write_text("\n".join(lines) + "\n")
    print(f"  Profile rebuilt: {profile_path}")
    _log(f"profile-update | Rebuilt from schema.json")


# ---------------------------------------------------------------------------
# Lint: Health check
# ---------------------------------------------------------------------------

def lint():
    """Check the knowledge base for issues."""
    print("Knowledge Lint")
    print("=" * 55)
    issues = []

    # Check static files exist
    for filename in ["double_entry.md", "chart_of_accounts.md", "common_transactions.md", "vat_rules.md", "compliance.md"]:
        if not (STATIC_DIR / filename).exists():
            issues.append(f"Missing static file: {filename}")

    # Check business profile
    profile_path = BUSINESS_DIR / "profile.md"
    if not profile_path.exists() or "Not yet generated" in profile_path.read_text():
        issues.append("Business profile not generated. Run: python knowledge/loader.py --rebuild-profile")

    # Check lessons for distillation opportunities
    if LESSONS_PATH.exists():
        lessons = json.loads(LESSONS_PATH.read_text())
        if len(lessons) >= 3:
            # Check for patterns
            patterns = Counter()
            for lesson in lessons:
                diff = lesson.get("diff", {})
                if diff:
                    patterns[json.dumps(diff, sort_keys=True)] += 1

            promotable = sum(1 for c in patterns.values() if c >= 3)
            if promotable:
                issues.append(f"{promotable} lesson pattern(s) ready to promote to rules. Run: python knowledge/loader.py --distill")

        # Lessons without reasons
        no_reason = sum(1 for l in lessons if not l.get("reason"))
        if no_reason:
            issues.append(f"{no_reason} lesson(s) missing a reason. Ask the accountant why they made the correction.")

    # Check index
    if not INDEX_PATH.exists():
        issues.append("Missing index.md")

    if issues:
        print(f"\n  Found {len(issues)} issue(s):\n")
        for issue in issues:
            print(f"  ! {issue}")
    else:
        print("\n  Everything looks good.")

    _log(f"lint | {len(issues)} issue(s) found")
    return issues


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(message: str):
    """Append to the knowledge log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = f"\n## [{date.today().isoformat()}] {message}\n"
    with open(LOG_PATH, "a") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Knowledge system manager")
    parser.add_argument("--lint", action="store_true", help="Health check the knowledge base")
    parser.add_argument("--distill", action="store_true", help="Promote repeated lessons to rules")
    parser.add_argument("--rebuild-profile", action="store_true", help="Regenerate business profile from schema")
    parser.add_argument("--show", action="store_true", help="Show knowledge summary")
    args = parser.parse_args()

    if args.lint:
        lint()
    elif args.distill:
        distill_rules()
    elif args.rebuild_profile:
        rebuild_profile()
    elif args.show:
        print("Knowledge System Summary")
        print("=" * 55)
        # Static
        static_files = list(STATIC_DIR.glob("*.md"))
        print(f"\n  Static knowledge: {len(static_files)} files")
        for f in static_files:
            lines = len(f.read_text().splitlines())
            print(f"    {f.name} ({lines} lines)")

        # Business
        print(f"\n  Business profile: {'exists' if (BUSINESS_DIR / 'profile.md').exists() else 'missing'}")
        print(f"  Preferences: {'exists' if (BUSINESS_DIR / 'preferences.md').exists() else 'missing'}")

        # Lessons
        lesson_count = 0
        if LESSONS_PATH.exists():
            lesson_count = len(json.loads(LESSONS_PATH.read_text()))
        rule_count = 0
        if RULES_PATH.exists():
            rule_count = len(json.loads(RULES_PATH.read_text()))
        print(f"\n  Lessons: {lesson_count}")
        print(f"  Rules: {rule_count}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
