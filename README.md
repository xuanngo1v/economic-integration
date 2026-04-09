# Ledger Pilot

AI bookkeeping assistant for Visma e-conomic. Connects to your accounting system, runs financial workflows, and learns from your accountant's corrections over time.

> The core architecture (knowledge system, learning loop, workflows) is API-agnostic. Contributions adding support for other accounting platforms (Xero, QuickBooks, Dinero, Billy, etc.) are welcome.

## Philosophy

1. **Ask first** — the agent always starts by asking what you want to achieve
2. **Explore before acting** — map out your setup, understand how your accountant works
3. **Read before write** — all analysis is read-only; write operations need explicit approval
4. **Explain simply** — output in business language, not account numbers
5. **Adapt, don't assume** — reads YOUR chart of accounts and adapts to how YOUR accountant set things up
6. **Never change without approval** — every write operation shows a preview and asks for confirmation

---

## What can the agent do?

The e-conomic REST API gives access to your full accounting system. Here's what's possible:

### Read (always safe, no changes)

| Capability | What it means |
|-----------|---------------|
| Chart of accounts | See how your accountant organized your books |
| Journal entries | Every transaction — revenue, costs, expenses |
| Booked invoices | All finalized invoices (sales + supplier) |
| Unpaid invoices | Who owes you money and how much |
| Overdue invoices | Which payments are late |
| Suppliers | Everyone you buy from |
| Customers | Everyone you sell to |
| Products | What you sell, at what price |
| Payment terms | How you get paid (net 8, 14, 30 etc.) |
| VAT setup | Your VAT configuration |
| Orders & quotes | Sales pipeline |

### Write (always requires your approval)

| Capability | What it means | Safety |
|-----------|---------------|--------|
| Create draft invoices | Prepare an invoice for a customer | Draft only — not sent until you book it |
| Create journal vouchers | Record an expense or transaction | Voucher only — not booked until accountant approves |
| Manage customers | Add or update customer records | Shows preview, asks for confirmation |
| Manage suppliers | Add or update supplier records | Shows preview, asks for confirmation |
| Manage products | Add or update product catalog | Shows preview, asks for confirmation |

**Important**: The agent creates DRAFTS and VOUCHERS. Your accountant always has the final say before anything is booked (finalized) in your accounting.

### Token permissions

When you grant API access, you choose a role:

| Role | What it allows |
|------|---------------|
| **SuperUser** | Full access — read everything, create everything |
| **Bookkeeping** | Accounting access — journals, entries, invoices, accounts |
| **Sales** | Customer-facing — invoices, customers, products, orders |

**Recommendation**: Start with **Bookkeeping** for accounting work. You can always upgrade later.

---

## Getting started

> **Full step-by-step guide**: See **[SETUP.md](SETUP.md)** — covers everything from installing Python to running your first report. Works for humans and AI agents.

### Prerequisites

- **Python 3.11+** — check with `python3 --version`. Install from [python.org](https://www.python.org/downloads/) or `brew install python` on Mac.
- **An e-conomic account** — Visma e-conomic subscription

### Step 1: Get your API tokens

You need two tokens:

**1a. App Secret Token**
1. Go to the [e-conomic Developer portal](https://secure.e-conomic.com/developer)
2. Log in with your e-conomic credentials
3. Under **Apps**, create a new app (or use an existing one)
4. Copy the **App Secret Token**

**1b. Agreement Grant Token**
1. In the developer portal, find your app
2. Click **Grant Access** to connect it to your company's agreement
3. Choose the role (Bookkeeping recommended to start)
4. Copy the **Agreement Grant Token**

> Full API docs: [restdocs.e-conomic.com](https://restdocs.e-conomic.com/#tl-dr)

### Step 2: Install

```bash
cd ledger-pilot

python3 -m venv venv
source venv/bin/activate    # Mac/Linux
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Step 3: Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your tokens:
```
ECONOMIC_APP_SECRET=your-actual-app-secret-token
ECONOMIC_AGREEMENT_TOKEN=your-actual-agreement-grant-token
```

### Step 4: Test connection

```bash
python run.py --test
```

You should see:
```
Testing e-conomic API connection...
  Connected to: Your Company Name (agreement 1234567)
```

### Step 5: Explore your setup

**Do this first** — before fetching data or running workflows:

```bash
python explore.py
```

This maps out your entire e-conomic setup (read-only):
- Company info and modules
- How your accountant structured the chart of accounts
- Active journals and what they're used for
- Suppliers, customers, products
- Current invoice status (drafts, unpaid, overdue)
- Payment terms and VAT setup
- Recent activity in the books

The explorer saves a full report to `data/explorer_report_YYYY-MM-DD.json`.

You can also explore one section at a time:
```bash
python explore.py --section accounts    # Just the chart of accounts
python explore.py --section invoices    # Just invoice status
python explore.py --section suppliers   # Just supplier list
```

### Step 6: Fetch & store data

```bash
python run.py                # Fetch last 90 days + store in SQLite
python run.py --days 365     # Fetch a full year
python run.py --fetch-only   # Just download JSON, don't store in DB
```

---

## Workflows

Ready-made accounting workflows in the `workflows/` folder. These are the things an AI agent can run for you.

### Analysis (read-only, always safe)

```bash
python workflows/pl_report.py              # P&L report (last month)
python workflows/pl_report.py --months 3   # Last quarter
python workflows/overdue_invoices.py        # Who owes you money?
python workflows/supplier_spend.py          # Where does your money go?
python workflows/cashflow_check.py          # Cash flow: in vs out
python workflows/prime_cost.py              # Prime cost ratio (COGS + Labor)
python workflows/monthly_comparison.py      # Month-over-month comparison
```

### Actions (write — always asks for confirmation)

```bash
python workflows/create_invoice.py --interactive   # Create a draft invoice
python workflows/journal_entry.py --interactive    # Create a journal entry
python workflows/bookkeeping.py --interactive      # Book supplier invoices / expenses
```

### Example output

**P&L Report** (`python workflows/pl_report.py`):
```
── Profit & Loss (P&L) ─────────────────────────
  Revenue:                      450,000
  Cost of goods (COGS):        -180,000
                                ────────────────
  Gross profit:                 270,000  (60.0%)

  Staff costs (labor):         -135,000
  Premises:                     -45,000
  Platform fees:                -22,500
  Administration:               -18,000
                                ────────────────
  Operating profit:              49,500

  Net profit (before tax):       45,000

── Key Ratios ───────────────────────────────────
  Gross margin:         60.0%
  COGS ratio:           40.0%
  Labor ratio:          30.0%
  Net margin:           10.0%
```

**Prime Cost** (`python workflows/prime_cost.py`):
```
── Prime Cost Breakdown ─────────────────────────
  Revenue:                      450,000
  Cost of goods (COGS):         180,000  (40.0%)
  Staff costs (Labor):          135,000  (30.0%)
                                ────────────────
  Prime Cost:                   315,000  (70.0%)

── Assessment ───────────────────────────────────
  Prime cost is 70.0% — Elevated.
  Above the 65% benchmark. Review COGS or labor costs.
```

**Overdue Invoices** (`python workflows/overdue_invoices.py`):
```
Total overdue: 42,500 across 5 invoices

  0-30 days: 3 invoices, 30,000
  30-60 days: 1 invoice, 7,500
  90+ days: 1 invoice, 5,000

  Top debtors:
  Customer A                          30,000  (2 invoices)
  Customer B                           7,500  (1 invoice)
```

---

## How to use with an AI agent (Claude, etc.)

If you're using this with Claude Code or another AI assistant:

### First conversation: "Help me understand my books"

The agent should:
1. Ask what you want to achieve (understand costs? track revenue? manage invoices?)
2. Run `python explore.py` to map your setup
3. Explain what it found in simple terms:
   - "You have 45 suppliers. Your top ones by volume are Supplier A and Supplier B."
   - "Your chart of accounts uses the 3000-range for cost of goods."
   - "You have 3 overdue invoices totaling 12,500."
4. Suggest what to look at next based on your goal

### Ongoing use: "What should I know this week?"

The agent can run a weekly check:
1. `python workflows/overdue_invoices.py` — anyone late on payments?
2. `python workflows/pl_report.py --months 1` — how did last month look?
3. `python workflows/supplier_spend.py` — any unusual spending?
4. `python workflows/cashflow_check.py` — cash position healthy?

### Pilot period: let the agent help with tasks

Start small:
1. **Week 1-2**: Agent only reads and reports. You learn to trust the data.
2. **Week 3-4**: Agent suggests draft invoices or journal entries. You review and approve.
3. **Month 2+**: Agent handles routine entries (recurring invoices, standard journal posts). Accountant reviews.

The agent should **always explain what it's doing and why**, in terms like:
- "I'm creating a draft invoice for Customer X because they ordered 50 units last week."
- "This journal entry records the supplier delivery from Monday — 8,500 on account 3010 (cost of goods)."

---

## Output

After running, the `data/` folder contains:

| File | Contents |
|------|----------|
| `explorer_report_YYYY-MM-DD.json` | Full setup mapping |
| `economic_invoices_YYYY-MM-DD.json` | All booked invoices |
| `economic_suppliers_YYYY-MM-DD.json` | Supplier directory |
| `economic_entries_YYYY-MM-DD.json` | Journal entries |
| `economic_accounts_YYYY-MM-DD.json` | Chart of accounts |
| `economic_data.db` | SQLite database |
| `overdue_report_YYYY-MM-DD.json` | Overdue invoice report |
| `pl_report_YYYY-MM-DD.json` | P&L report |
| `supplier_spend_YYYY-MM-DD.json` | Supplier analysis |
| `cashflow_YYYY-MM-DD.json` | Cash flow check |

### Query the database directly

```sql
sqlite3 data/economic_data.db

-- Top suppliers by spend
SELECT supplier_name, SUM(amount) as total
FROM supplier_invoices GROUP BY supplier_name ORDER BY total DESC LIMIT 10;

-- Monthly revenue
SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
FROM financial_entries WHERE entry_type = 'revenue' GROUP BY month ORDER BY month;
```

---

## Run on a schedule (optional)

```bash
# Daily at 08:00 (cron)
crontab -e
0 8 * * * cd /path/to/ledger-pilot && venv/bin/python run.py >> data/run.log 2>&1
```

---

## Customization

### Account categories

The P&L categories are defined in `account_map.py` (the single source of truth). Default ranges:

| Range | Category |
|-------|----------|
| 1000-1999 | Revenue |
| 2000-2999 | Cost of goods (COGS) |
| 3000-3999 | Staff costs (Labor) |
| 4000-4299 | Premises |
| 4300-4399 | Transport |
| 4400-4599 | Platform fees |
| 4600-4699 | Other operating |
| 4700-4999 | Administration |
| 5000-5499 | Depreciation |
| 5500-5599 | Financial income |
| 5600-5999 | Financial expense |
| 6000-6999 | Tax |
| 7000+ | Balance sheet (not P&L) |

If your accountant uses different ranges, edit `account_map.py` — all workflows import from there. Run `python explore.py --section accounts` to see your actual setup first.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ERROR: tokens required` | Copy `.env.example` to `.env` and add your tokens |
| `HTTP 401` | Tokens are wrong or expired — regenerate in developer portal |
| `HTTP 403` | App doesn't have access to this agreement, or wrong role — re-grant |
| `No data files found` | Run `python fetch.py` before `python ingest.py` |
| `0 invoices / 0 entries` | Account may be empty or date range too narrow — try `--days 365` |

---

## All commands via run.py

```bash
python run.py              # Fetch data + store in SQLite
python run.py --test       # Test API connection
python run.py --explore    # Map your full e-conomic setup
python run.py --schema     # Build fast-reference schema index
python run.py --health     # Health check + auto-fix issues
python run.py --suggest    # Get workflow suggestions
python run.py --log        # View activity history
```

---

## Files

```
ledger-pilot/
├── README.md                  # This file
├── CONTRIBUTING.md            # How to contribute
├── LICENSE                    # MIT License
├── LLM.md                    # Instructions for AI agents
├── SETUP.md                  # Step-by-step setup guide
├── Makefile                   # Shortcuts: make test, make fetch, make pl, etc.
├── .env.example               # Token template
├── requirements.txt           # Python dependencies
│
├── api.py                     # Shared API module (auth, get, get_all, count)
├── account_map.py             # Account categorization (single source of truth)
├── run.py                     # Single entry point for everything
├── fetch.py                   # Download data from e-conomic API
├── ingest.py                  # Load JSON into SQLite
├── explore.py                 # Map your full e-conomic setup (read-only)
├── schema.py                  # Build fast-reference index
├── healthcheck.py             # Detect changes, self-heal, verify tokens
├── log.py                     # Activity log — history of everything done
│
├── workflows/                 # Accounting workflows
│   ├── TEMPLATE.py                # Template for building new workflows
│   ├── suggest.py                 # Suggest next actions based on state
│   ├── pl_report.py               # Profit & Loss report
│   ├── prime_cost.py              # Prime cost ratio (COGS + Labor / Revenue)
│   ├── monthly_comparison.py      # Month-over-month P&L comparison
│   ├── overdue_invoices.py        # Overdue invoices + aging
│   ├── supplier_spend.py          # Supplier spend analysis
│   ├── cashflow_check.py          # Cash flow: incoming vs outgoing
│   ├── bookkeeping.py             # Book supplier invoices & expenses (write)
│   ├── create_invoice.py          # Create draft invoice (write)
│   ├── journal_entry.py           # Create journal voucher (write)
│   └── review_corrections.py      # Auto-capture accountant corrections
│
├── knowledge/                 # AI knowledge base (LLM Wiki pattern)
│   ├── index.md                   # Knowledge catalog — AI reads this first
│   ├── log.md                     # Chronological record of changes
│   ├── loader.py                  # Load/add/distill knowledge
│   ├── ingest.py                  # Seed knowledge from transaction data
│   ├── static/                    # Bookkeeping fundamentals
│   │   ├── double_entry.md
│   │   ├── chart_of_accounts.md
│   │   ├── common_transactions.md
│   │   ├── vat_rules.md
│   │   └── compliance.md
│   ├── business/                  # Your business (auto-generated + learned)
│   │   ├── profile.md
│   │   ├── patterns.md
│   │   └── preferences.md
│   └── lessons/                   # Learning from corrections
│       ├── lessons.json
│       └── rules.json
│
├── tests/                     # Test suite (37 tests)
│   ├── test_account_map.py
│   └── test_loader.py
│
└── data/                      # Fetched data + reports (gitignored)
    ├── schema.json
    ├── activity_log.json
    ├── economic_data.db
    └── *.json
```
