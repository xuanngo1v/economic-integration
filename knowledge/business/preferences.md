# Preferences

How the user and accountant want things done. Updated over time as
the AI learns from interactions and corrections.

Add preferences with:
```python
from knowledge.loader import add_preference
add_preference("journal_selection", "Always use journal 6 for supplier invoices", "user")
```

## Status: No preferences recorded yet

As you use the system, preferences will be captured here. Examples of
what gets recorded:

- Which journal to use for different entry types
- Preferred account for specific expense categories
- How to handle ambiguous transactions
- Reporting preferences (monthly, quarterly, etc.)
- Communication style (technical vs plain language)
