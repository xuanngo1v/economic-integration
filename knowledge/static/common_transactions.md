# Common Transactions

The 10 transaction types that cover 90% of bookkeeping.

## 1. Supplier Invoice (Purchase)

When you receive a bill from a supplier.

| Account | Debit | Credit |
|---------|-------|--------|
| Expense account (e.g. COGS, rent) | Net amount | |
| Input VAT | VAT amount | |
| Accounts payable / Supplier | | Gross amount |

- The expense account depends on WHAT you bought (food → COGS, rent → premises)
- VAT is typically 25% of the net amount (purchase VAT / input VAT)
- In e-conomic: posted as a supplier invoice voucher in the appropriate journal

## 2. Customer Invoice (Sale)

When you send an invoice to a customer.

| Account | Debit | Credit |
|---------|-------|--------|
| Accounts receivable / Customer | Gross amount | |
| Revenue account | | Net amount |
| Output VAT | | VAT amount |

- Revenue account depends on WHAT you sold
- Output VAT is what you owe to tax authorities
- In e-conomic: created as a draft invoice, booked by accountant

## 3. Expense Payment (Direct)

When you pay an expense directly (e.g. card payment, bank transfer).

| Account | Debit | Credit |
|---------|-------|--------|
| Expense account | Net amount | |
| Input VAT | VAT amount | |
| Bank account | | Gross amount |

## 4. Receive Payment (Customer Pays)

When a customer pays their invoice.

| Account | Debit | Credit |
|---------|-------|--------|
| Bank account | Amount received | |
| Accounts receivable | | Amount received |

- The original invoice is cleared
- No VAT impact — VAT was recorded when the invoice was created

## 5. Pay Supplier

When you pay a supplier invoice.

| Account | Debit | Credit |
|---------|-------|--------|
| Accounts payable / Supplier | Amount paid | |
| Bank account | | Amount paid |

## 6. Payroll

Recording salary payments.

| Account | Debit | Credit |
|---------|-------|--------|
| Salary expense | Gross salary | |
| Payroll tax expense | Employer contributions | |
| Tax withholding (liability) | | Employee tax |
| Pension (liability) | | Pension contribution |
| Bank account | | Net pay |

- Payroll is complex — multiple lines for tax, pension, benefits
- Usually handled by payroll software, then booked as a journal entry

## 7. Depreciation

Monthly reduction of asset value.

| Account | Debit | Credit |
|---------|-------|--------|
| Depreciation expense | Monthly amount | |
| Accumulated depreciation (asset) | | Monthly amount |

- Straight-line: cost / useful life = monthly depreciation
- Only for assets above a threshold (varies by jurisdiction)

## 8. Accrual (Prepaid Expense)

When you pay in advance for something (e.g. annual insurance).

| At payment: | Debit | Credit |
|-------------|-------|--------|
| Prepaid expense (asset) | Full amount | |
| Bank | | Full amount |

| Monthly: | Debit | Credit |
|----------|-------|--------|
| Insurance expense | Monthly portion | |
| Prepaid expense (asset) | | Monthly portion |

## 9. VAT Settlement

When you file and pay VAT to tax authorities.

| Account | Debit | Credit |
|---------|-------|--------|
| Output VAT (what you owe) | Total output | |
| Input VAT (what you're owed) | | Total input |
| VAT payable/receivable | Difference | |

- If output > input: you owe money (pay the difference)
- If input > output: you get a refund

## 10. Year-End Closing

Transfer P&L result to equity.

| Account | Debit | Credit |
|---------|-------|--------|
| Revenue accounts | Total revenue | |
| Expense accounts | | Total expenses |
| Retained earnings (equity) | | Net profit |

- All P&L accounts reset to zero for the new year
- The net result moves to the balance sheet

## For the AI: Decision Tree

When booking a transaction, ask:
1. **What happened?** → Determines the transaction type above
2. **What accounts?** → Check `account_map.py` and `schema.json`
3. **Is there VAT?** → Check `vat_rules.md`
4. **Which journal?** → Check business profile for journal assignments
5. **Any lessons/rules?** → Check `lessons/rules.json` for past corrections
