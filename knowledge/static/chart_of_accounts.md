# Chart of Accounts

The chart of accounts is the backbone of any accounting system. It's the list of
all accounts used to categorize every transaction.

## Account Types

| Type | What it tracks | Examples |
|------|---------------|----------|
| **Assets** | What you own | Bank, cash, receivables, inventory, equipment |
| **Liabilities** | What you owe | Payables, loans, tax owed, VAT payable |
| **Equity** | Owner's stake | Share capital, retained earnings |
| **Revenue** | Money earned | Sales, service income, other income |
| **Expenses** | Money spent | Supplies, rent, salaries, utilities |

## Standard Structure (by number range)

Most accounting systems group accounts by number ranges. A typical structure:

| Range | Category | Financial Statement |
|-------|----------|-------------------|
| 1000-1999 | Assets | Balance Sheet |
| 2000-2999 | Revenue | P&L (Income Statement) |
| 3000-3999 | Cost of goods / COGS | P&L |
| 4000-4999 | Operating expenses | P&L |
| 5000-5999 | Other expenses | P&L |
| 6000-6999 | Tax | P&L |
| 7000-7999 | Balance sheet items | Balance Sheet |
| 8000-8999 | Financial items | P&L |
| 9000-9999 | Equity / closing | Balance Sheet |

**Important:** Every business customizes this. The ranges above are defaults.
Always check the actual chart of accounts via `explore.py` or `schema.json`.
The file `account_map.py` contains the actual mapping for THIS business.

## Heading Accounts vs Posting Accounts

- **Heading accounts** — organizational labels, you can't post to them
- **Posting accounts** — where transactions actually go
- **Balance sheet accounts** — track assets, liabilities, equity (type: "status")
- **P&L accounts** — track revenue and expenses (type: "profitAndLoss")

## How the AI Should Use This

1. **Never assume account ranges** — always read `account_map.py` or `schema.json`
2. **Check account type before posting** — don't post to a heading account
3. **Match the accountant's structure** — if they use 2010 for food purchases, use 2010
4. **When unsure, show options** — list relevant accounts and let the user choose
