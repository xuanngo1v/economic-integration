# Instructions for AI Agents

You are working with an e-conomic (Visma e-conomic) integration for a business. This file tells you how to operate.

## If this is a fresh setup

If `data/schema.json` does not exist and `.env` does not exist, the project hasn't been set up yet. Walk the user through **SETUP.md** step by step:

1. Read `SETUP.md` and follow it with the user
2. Help them get Python installed if needed
3. Guide them through getting API tokens from `secure.e-conomic.com`
4. Help them configure `.env`
5. Run `python run.py --test` to verify
6. Run `python run.py --explore` to map their setup
7. Run `python run.py --schema` to build the index
8. Then ask what they want to do

Be patient — the user may not be technical. Explain each step in plain language. The token setup (Step 3 in SETUP.md) is where most people get stuck.

## First rule: Ask what the user wants

Before running anything, ask:
- "What would you like to do with your accounting data?"
- Understand their goal: review finances? check who owes them money? create an invoice? understand costs?
- Then pick the right tool for the job.

## Session start protocol (after setup is complete)

Every time you start working with this project:

1. **Read `data/schema.json`** — this is the fast-reference index of the entire e-conomic setup (accounts, suppliers, customers, journals, API endpoints). If it doesn't exist, run `python schema.py` first.
2. **Read `knowledge/index.md`** — the knowledge base index. Find what knowledge exists and what's relevant.
3. **Read `data/activity_log.json`** (last 10 entries) — what happened recently? Any pending reviews?
4. **Run `python healthcheck.py`** — check if tokens work, schema is fresh, anything changed.
5. **Then ask the user** what they want to do.

## Knowledge system

The `knowledge/` folder is a persistent, compounding knowledge base. It gets smarter
over time as the accountant corrects entries and the user states preferences.

### Before any write operation:
```python
from knowledge.loader import load_knowledge
k = load_knowledge("supplier_invoice", context={"supplier": "Supplier X"})
# Check k["rules"] first — these are verified patterns from past corrections
# Check k["lessons"] — individual corrections that may be relevant
# Read k["static"] — bookkeeping fundamentals for this task type
```

### After a correction is detected:
```python
from knowledge.loader import add_lesson
add_lesson(
    original={"account": 2000, "vat": "I25"},
    corrected={"account": 2010, "vat": "I25"},
    context={"task_type": "supplier_invoice", "supplier": "Supplier X"},
    reason="Food purchases go to 2010"
)
```

### When the user states a preference:
```python
from knowledge.loader import add_preference
add_preference("journal_selection", "Always use journal 6 for supplier invoices", "user")
```

### Periodically:
- Run `python knowledge/loader.py --lint` to health-check the knowledge base
- Run `python knowledge/loader.py --distill` to promote repeated lessons into rules

## How to talk about accounting

Use simple business language. The user is a business owner, not an accountant.

| Don't say | Say instead |
|-----------|-------------|
| "Account 3010 debited 45,000" | "You spent 45,000 on food supplies" |
| "Debit/credit imbalance on voucher" | "The journal entry doesn't balance — one side is missing" |
| "P&L shows negative EBITDA" | "You're spending more than you're earning this month" |
| "Account range 4000-4999" | "Your staff costs (salaries, benefits, etc.)" |
| "Accounts receivable aging" | "Invoices that customers haven't paid yet" |

But also be ready to use proper accounting terms if the user or their accountant asks — adapt to who you're talking to.

## The tools available to you

### Core scripts
| Script | What it does | Safe? |
|--------|-------------|-------|
| `python run.py --test` | Test API connection | Yes |
| `python run.py` | Fetch all data + store in SQLite | Yes (read from API, write locally) |
| `python run.py --explore` | Map the full e-conomic setup | Yes (read-only) |
| `python explore.py` | Detailed setup exploration | Yes (read-only) |
| `python schema.py` | Build/update the schema index | Yes (read from API, write locally) |
| `python healthcheck.py` | Check for issues and changes | Yes (read-only) |
| `python healthcheck.py --fix` | Auto-repair stale schema | Yes (rebuilds local files) |
| `python log.py` | View activity history | Yes |

### Workflows (read-only, always safe)
| Workflow | When to suggest it |
|----------|-------------------|
| `python workflows/suggest.py` | User isn't sure what to do — show them options |
| `python workflows/overdue_invoices.py` | User asks about payments, cash, who owes them |
| `python workflows/pl_report.py --months N` | User asks about profit, revenue, costs, margins |
| `python workflows/supplier_spend.py --days N` | User asks about expenses, suppliers, spending |
| `python workflows/cashflow_check.py` | User asks about cash position or liquidity |

### Workflows (write — ALWAYS ask before running)
| Workflow | What it creates | Safety |
|----------|----------------|--------|
| `python workflows/create_invoice.py --interactive` | Draft invoice | NOT booked — accountant reviews |
| `python workflows/journal_entry.py --interactive` | Journal voucher | NOT booked — accountant reviews |

## Rules for write operations

1. **Never write without explaining first.** Show the user exactly what you plan to create.
2. **Never book anything.** Only create DRAFTS and VOUCHERS. The accountant books them.
3. **Log everything.** After any write, call `log_action("write", "description of what was created")`.
4. **Mark for review.** Use `requires_review=True` when logging write actions.
5. **If unsure, don't.** It's always safe to just read and report. Ask the user before creating anything.

## How to use schema.json

`data/schema.json` is your cheat sheet. Instead of calling the API to look up an account number or supplier name, read the schema:

```python
import json
schema = json.loads(open("data/schema.json").read())

# Look up an account
account = schema["accounts"]["lookup"]["3010"]
# → {"number": 3010, "name": "Cost of goods, food", "type": "profitAndLoss", "category": "cogs"}

# Look up a supplier
supplier = schema["suppliers"]["lookup"]["12"]
# → {"number": 12, "name": "Example Supplier", "city": "Copenhagen"}

# Check API endpoint info
endpoint = schema["api_index"]["endpoints"]["/invoices/drafts"]
# → {"method": "GET/POST", "description": "Draft invoices — POST to create new draft"}

# Check current counts
schema["counts"]["invoices_overdue"]  # → 3
```

If schema.json is missing or stale, run `python schema.py` to rebuild it.

## How to use the activity log

Log everything meaningful:

```python
from log import log_action, log_error, log_note, log_change

# After fetching data
log_action("fetch", "Fetched 145 invoices and 89 entries for last 90 days")

# After running a workflow
log_action("workflow", "P&L report: revenue 450K, net profit 85K, gross margin 62%",
           details={"revenue": 450000, "net_profit": 85000})

# After a write operation (always mark for review)
log_action("write", "Created draft invoice #1234 for Customer X, 12,500",
           requires_review=True)

# When something fails
log_error("fetch", "HTTP 401 — token may have expired")

# When the user mentions a preference
log_note("User wants weekly P&L every Monday morning")

# When the environment changes
log_change("suppliers", "45", "47", source="healthcheck")
```

## Self-healing behavior

When you detect something has changed:

1. **Schema out of date** → Run `python schema.py` to rebuild
2. **New accounts added** → Rebuild schema, check if category mapping still works
3. **Token expired (401)** → Tell the user to regenerate tokens in the developer portal
4. **Fewer entries than expected** → Could be normal (quiet period) or a sign bookkeeping is behind — ask, don't assume
5. **New supplier/customer** → Update schema, mention it to the user ("I see a new supplier was added: X")

Always log changes with `log_change()` so there's a record.

## Adapting to the accountant's setup

**Never assume a standard chart of accounts.** Read the actual chart of accounts from schema.json or explore.py.

- If the user's accountant uses account 3500 for food supplies instead of 3010, adapt.
- If they have custom account categories, explain what you see rather than what you expect.
- If the account structure doesn't match the standard standard ranges, warn the user that the auto-categorization in workflows might need adjustment.

**The accountant's structure is the truth. Your category mapping is a convenience.**

## Suggesting next steps

After completing any task, suggest what might be useful next:

- After P&L report → "Want me to dig into where staff costs went up?"
- After overdue check → "Should I draft reminder emails for the top 3 debtors?"
- After supplier analysis → "Your top supplier is 40% of spend. Want me to check if there are alternative quotes?"
- After fetching data → "I can run a P&L, check overdue invoices, or analyze supplier spending. What's most useful?"

## Building new workflows with the user

When the user asks a question that no existing workflow answers, build one together.

### Process

1. **Understand the question**: "I want to know which months we spend the most on food" → this is a cost trend analysis by account category and month.
2. **Check if a workflow already exists**: Look in `workflows/` — maybe an existing one can be adjusted.
3. **If not, create one**:
   - Copy `workflows/TEMPLATE.py` to a new file with a descriptive name (e.g. `workflows/cost_trends.py`)
   - Fill in the logic using the API endpoints from `data/schema.json`
   - Use `load_schema()` for account/supplier lookups instead of extra API calls
   - Print results in plain language
   - Save a report to `data/`
   - Log the action
4. **Show the user what it does**: Run it, explain the output, ask if they want adjustments.
5. **Iterate**: "Can you also split it by supplier?" → update the workflow.
6. **It's now reusable**: Next time they ask the same question, just run the workflow.

### Naming conventions

- Lowercase with underscores: `cost_trends.py`, `invoice_turnaround.py`
- Name describes the question it answers, not the technical implementation
- Keep the docstring at the top clear — future agents read it to decide which workflow to suggest

### Available API data for workflows

From `data/schema.json` → `api_index.endpoints`:

**Financial data:**
- `/entries` — all journal entries, filterable by date. This is the richest data source.
- `/invoices/booked` — finalized invoices
- `/invoices/unpaid`, `/invoices/overdue` — outstanding money
- `/accounts` — chart of accounts with types and categories

**Business data:**
- `/customers` — who you sell to
- `/suppliers` — who you buy from
- `/products` — what you sell
- `/orders/drafts`, `/orders/sent` — sales pipeline

**Reference data:**
- `/payment-terms` — payment term definitions
- `/vat-accounts` — VAT rates and codes
- `/departments` — if the business uses departmental accounting

### Filtering entries (the most common operation)

```python
# Last 90 days of entries
entries = _get_all("/entries", params={
    "pagesize": 1000,
    "filter": "date$gte$2026-01-01$and$date$lte$2026-03-31",
})

# Filter by account range (e.g. only COGS accounts 3000-3999)
cogs_entries = [e for e in entries
    if 3000 <= (e.get("account", {}).get("accountNumber") or 0) <= 3999]
```

## What NOT to do

- Don't delete data files without asking
- Don't modify the chart of accounts through the API
- Don't book invoices or vouchers — only create drafts
- Don't assume the chart of accounts follows standard ranges — check first
- Don't run write operations without explicit user approval
- Don't display API tokens or credentials
- Don't make changes to the accountant's structure without the accountant's approval
