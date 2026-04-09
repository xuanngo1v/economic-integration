# Workflows

These are accounting workflows an AI agent can run against your e-conomic data.
Each workflow is a standalone script that does ONE thing well.

## Important rules

1. **Always explore first** — run `python explore.py` before any workflow so you understand how the accounting is set up
2. **Read-only by default** — workflows that read data run without confirmation
3. **Write operations need approval** — anything that creates or changes data will ask for confirmation first
4. **Adapt to the accountant's setup** — these workflows read your chart of accounts and adapt to YOUR account structure, not a hardcoded one
5. **Explain in plain language** — output is written for business owners, not accountants

## Available workflows

| Workflow | What it does | Read/Write |
|----------|-------------|------------|
| `suggest.py` | Analyze state and suggest what to do next | Read-only |
| `pl_report.py` | Profit & Loss report, adapts to your chart of accounts | Read-only |
| `prime_cost.py` | Prime cost ratio: (COGS + Labor) / Revenue | Read-only |
| `monthly_comparison.py` | Month-over-month P&L comparison with change alerts | Read-only |
| `overdue_invoices.py` | Find overdue invoices, aging breakdown, top debtors | Read-only |
| `supplier_spend.py` | Top suppliers, spend trends, concentration analysis | Read-only |
| `cashflow_check.py` | Cash flow: incoming vs outgoing, net position | Read-only |
| `bookkeeping.py` | Book supplier invoices and expenses | Write |
| `create_invoice.py` | Create a draft invoice (requires approval) | Write |
| `journal_entry.py` | Create a journal entry / finance voucher (requires approval) | Write |
| `review_corrections.py` | Auto-capture accountant corrections as lessons | Read-only |

## Running a workflow

```bash
# Activate your environment first
source venv/bin/activate

# Run any workflow
python workflows/overdue_invoices.py
python workflows/pl_report.py --months 3
python workflows/supplier_spend.py --days 90
```

## Creating new workflows together

You and an AI agent can build new workflows anytime. There's a template to start from.

### How it works

1. **You describe the question** — e.g. "I want to see which months we spend the most on food supplies"
2. **The agent builds it** — using `TEMPLATE.py` as the starting point
3. **You review and adjust** — "Can you also break it down by supplier?" / "Add a comparison to last year"
4. **It becomes a reusable workflow** — saved in this folder, logged, available next time

### Starting a new workflow

```bash
# Copy the template
cp workflows/TEMPLATE.py workflows/my_new_workflow.py
```

Or just tell the AI agent: "Let's make a workflow that [does X]" — it knows to use the template.

### Template structure

Every workflow follows the same pattern:
1. Load schema for fast lookups
2. Fetch data from the API
3. Analyze
4. Print results in plain language
5. Save report to `data/`
6. Log the action

### Workflow ideas

Here are workflows that could be useful — tell the agent to build any of these:

| Idea | What it answers |
|------|----------------|
| Monthly comparison | "How did this month compare to last month?" |
| Seasonal trends | "Which months are strongest/weakest for revenue?" |
| Cost category breakdown | "What % goes to food, staff, rent, other?" |
| Supplier price tracking | "Has my top supplier gotten more expensive over time?" |
| Customer revenue ranking | "Who are my best customers by revenue?" |
| Invoice turnaround | "How fast do customers pay on average?" |
| VAT summary | "What's my VAT for this quarter?" |
| Budget vs actual | "Am I over or under budget on staff costs?" |
| Recurring expenses | "What are my fixed monthly costs?" |
| Year-over-year | "How does 2026 compare to 2025 so far?" |
| Product profitability | "Which products/services make the most money?" |
| Expense anomaly | "Any unusual charges this month?" |

## For AI agents

If you are an AI agent using these workflows:

1. **Start by asking the user**: What do you want to achieve? Understand their goal before picking a workflow.
2. **Run explore.py first**: Map out the setup. Understand the chart of accounts, active journals, supplier list.
3. **Explain what you find**: Use simple business language. "You spent 45,000 currency on your top supplier last month" not "Account 3010 debited 45,000".
4. **Never write without approval**: Show the user what you plan to create. Let them confirm or adjust.
5. **Suggest next steps**: After running a workflow, suggest what else might be useful based on what you found.
6. **Build new workflows with the user**: When they ask a question no existing workflow answers, create one together using `TEMPLATE.py`. Save it so it's reusable next time.
