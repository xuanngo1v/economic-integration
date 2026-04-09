# Setup Guide

Step-by-step setup for connecting to your e-conomic accounting system.
This guide works whether you're setting it up yourself or an AI agent is helping you.

---

## Before you start

You need:
- A computer with **Python 3.11+** installed
- A **Visma e-conomic** subscription (the accounting software)
- About 15 minutes

### Check Python

Open Terminal (Mac) or Command Prompt (Windows) and run:

```bash
python3 --version
```

If it says `Python 3.11` or higher, you're good. If not:
- **Mac**: `brew install python` or download from [python.org](https://www.python.org/downloads/)
- **Windows**: Download from [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install

---

## Step 1: Get the project files

If someone sent you a zip file:
```bash
# Unzip it somewhere you can find it
unzip economic-integration.zip -d ~/Desktop/
cd ~/Desktop/economic-integration
```

If you're cloning from git:
```bash
cd ~/Desktop
git clone <repo-url> economic-integration
cd economic-integration
```

---

## Step 2: Set up Python environment

```bash
# Create a virtual environment (keeps things clean)
python3 -m venv venv

# Activate it
source venv/bin/activate        # Mac / Linux
# venv\Scripts\activate         # Windows

# Install the two dependencies
pip install -r requirements.txt
```

You should see `requests` and `python-dotenv` install. That's it — only 2 packages.

---

## Step 3: Get your e-conomic API tokens

This is the most important step. You need two tokens from e-conomic.

### 3a: Log in to e-conomic

1. Go to **[secure.e-conomic.com](https://secure.e-conomic.com)**
2. Log in with your normal e-conomic credentials

### 3b: Open the developer settings

1. Click the **gear icon** (Settings) in the top right
2. Find **Developer** or **Apps & integrations** in the menu
3. You should see a page about API access and connected apps

> If you can't find developer settings, your e-conomic plan may not include API access,
> or your user role doesn't have permission. Ask whoever manages your e-conomic account.

### 3c: Create an app (or find an existing one)

1. Click **Create app** or **Add**
2. Give it a name, e.g. "AI Accounting Assistant"
3. For role, choose:
   - **Bookkeeping** — if you mainly want to read financial data and create journal entries
   - **SuperUser** — if you want full access to everything
4. You'll get an **App Secret Token** — **copy it and save it somewhere safe**

### 3d: Grant access to your agreement

1. Find your new app in the list
2. Click **Grant access** or a similar button
3. This connects the app to your company's data
4. You'll get an **Agreement Grant Token** — **copy it and save it**

> **Important**: These tokens give access to your accounting data. Treat them like passwords.
> Don't share them, don't post them online, don't commit them to git.

### Having trouble?

| Problem | Solution |
|---------|----------|
| Can't find developer settings | You may need admin access. Ask your e-conomic admin. |
| No "Create app" button | Your subscription plan may not include API. Contact e-conomic support. |
| "Insufficient permissions" | Your user role needs developer access. Ask your admin to enable it. |
| Already have tokens from before | You can reuse them — skip to Step 4. |

> Full API documentation: [restdocs.e-conomic.com](https://restdocs.e-conomic.com/#tl-dr)

---

## Step 4: Configure your tokens

```bash
# Copy the template
cp .env.example .env
```

Open `.env` in any text editor (TextEdit, Notepad, VS Code, nano — anything works):

```
ECONOMIC_APP_SECRET=paste-your-app-secret-token-here
ECONOMIC_AGREEMENT_TOKEN=paste-your-agreement-grant-token-here
```

Replace the placeholder text with your actual tokens. No quotes needed.

Save the file.

---

## Step 5: Test the connection

```bash
python run.py --test
```

**If it works**, you'll see:
```
Testing e-conomic API connection...
  Connected to: Your Company Name (agreement 1234567)
```

**If it fails:**

| Error | What to do |
|-------|-----------|
| `ERROR: Tokens not found` | Check that `.env` exists and has both tokens filled in |
| `HTTP 401` | Token is wrong or expired. Go back to Step 3 and copy the tokens again. |
| `HTTP 403` | The app doesn't have permission. Re-grant access in the developer portal. |
| `Connection error` | Check your internet connection. The API is at `restapi.e-conomic.com`. |

---

## Step 6: Explore your setup

Now that the connection works, map out your entire e-conomic system:

```bash
python run.py --explore
```

This is **read-only** — it just looks at how things are set up. You'll see:
- Your company name and agreement
- How the chart of accounts (chart of accounts) is organized
- What journals exist and what they're used for
- Your suppliers, customers, and products
- Current invoice status (any unpaid? any overdue?)
- Payment terms and VAT configuration

The full report is saved to `data/explorer_report_YYYY-MM-DD.json`.

---

## Step 7: Build the schema index

This creates a fast-reference file that AI agents use for instant lookups:

```bash
python run.py --schema
```

Creates `data/schema.json` — a single file with your full account chart, supplier list,
customer list, API endpoint map, and current counts. Agents read this instead of
calling the API every time they need to look something up.

---

## Step 8: Fetch your data

Pull your financial data into a local database:

```bash
python run.py
```

This fetches invoices, suppliers, journal entries, and chart of accounts for the last 90 days,
then stores everything in `data/economic_data.db` (SQLite).

For more history:
```bash
python run.py --days 365    # Full year
```

---

## Step 9: Try a workflow

See what the system suggests based on your data:

```bash
python run.py --suggest
```

Or run a specific report:

```bash
# Who owes you money?
python workflows/overdue_invoices.py

# How's the P&L looking?
python workflows/pl_report.py --months 3

# Where does your money go?
python workflows/supplier_spend.py
```

---

## You're done!

Your setup is complete. Here's what you have:

| Command | What it does |
|---------|-------------|
| `python run.py --test` | Verify tokens still work |
| `python run.py --explore` | Map your e-conomic setup |
| `python run.py --schema` | Update the fast-reference index |
| `python run.py --health` | Check for issues + auto-fix |
| `python run.py --suggest` | What should I do next? |
| `python run.py --log` | What's been done so far? |
| `python run.py` | Fetch latest data |

### For AI agents

If you're handing this off to an AI agent (Claude Code, etc.):

1. Point the agent to this project folder
2. Tell it to read `LLM.md` — that's the agent instruction manual
3. The agent will follow the session protocol: read schema → read knowledge → check health → ask what you want

### Knowledge base

The knowledge system seeds automatically:
- `python run.py --explore` → generates a business profile in `knowledge/business/`
- `python run.py` (fetch + ingest) → learns transaction patterns from your data
- Over time, accountant corrections are captured and the AI gets smarter

See `knowledge/README.md` for the full architecture.

### Next steps

- **Run daily**: Set up a cron job to fetch data automatically (see README.md)
- **Weekly review**: Run `python run.py --suggest` every Monday
- **Review corrections**: Run `python workflows/review_corrections.py` to capture what the accountant changed
- **Add workflows**: The `workflows/` folder is designed to grow — add custom reports as you need them

---

## Quick reference: all files

```
economic-integration/
├── SETUP.md               # This guide
├── README.md              # Full documentation
├── LLM.md                 # AI agent instructions
├── .env.example           # Token template
├── .env                   # Your tokens (never share!)
├── requirements.txt       # Python dependencies (just 2)
├── run.py                 # Single entry point for everything
├── fetch.py               # Download from e-conomic API
├── ingest.py              # Store in SQLite database
├── explore.py             # Map your setup (read-only)
├── schema.py              # Build fast-reference index
├── healthcheck.py         # Detect changes + self-heal
├── log.py                 # Activity history
└── workflows/             # Accounting workflows
    ├── suggest.py             # Suggest next actions
    ├── overdue_invoices.py    # Who owes you money?
    ├── pl_report.py           # Profit & Loss
    ├── supplier_spend.py      # Supplier spending analysis
    ├── cashflow_check.py      # Cash flow overview
    ├── create_invoice.py      # Create draft invoice (needs approval)
    └── journal_entry.py       # Create journal entry (needs approval)
```

---

## If something breaks later

```bash
# First: check what's wrong
python run.py --health

# If tokens expired: get new ones from secure.e-conomic.com (Step 3)
# If schema is stale: it auto-fixes with --health
# If data looks wrong: re-fetch with python run.py --days 365
# If you're lost: python run.py --suggest
```
