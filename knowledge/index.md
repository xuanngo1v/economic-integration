# Knowledge Index

AI: read this file first to find relevant knowledge for your current task.

## Static Knowledge (bookkeeping fundamentals)

- [Double-Entry Bookkeeping](static/double_entry.md) — debits, credits, the accounting equation, why entries must balance
- [Chart of Accounts](static/chart_of_accounts.md) — account structure, types, how to read a chart of accounts
- [Common Transactions](static/common_transactions.md) — how to book supplier invoices, expenses, revenue, payroll, depreciation
- [VAT Rules](static/vat_rules.md) — purchase vs sales VAT, rates, exemptions, reverse charge
- [Compliance](static/compliance.md) — record retention, audit trails, fiscal years, digital bookkeeping requirements

## Business Knowledge (specific to this company)

- [Business Profile](business/profile.md) — company setup, account structure, journals, common patterns
- [Learned Patterns](business/patterns.md) — transaction patterns detected from existing data (auto-generated)
- [Preferences](business/preferences.md) — how the user/accountant wants things done

## Learned Knowledge (from corrections)

- [Lessons](lessons/lessons.json) — individual corrections the accountant made to AI-proposed entries
- [Rules](lessons/rules.json) — stable patterns distilled from repeated lessons

## Task-to-Knowledge Map

| When doing this... | Read these pages |
|--------------------|------------------|
| Booking a supplier invoice | common_transactions, vat_rules, profile, preferences, rules |
| Recording an expense | common_transactions, vat_rules, profile, rules |
| Creating a draft invoice | common_transactions, vat_rules, profile |
| Explaining accounting concepts | double_entry, chart_of_accounts |
| Running a P&L or report | chart_of_accounts, profile |
| Checking compliance | compliance, vat_rules |
| Any write operation | Always check rules.json and lessons.json first |
