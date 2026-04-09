# VAT Rules

Value Added Tax (VAT) applies to most business transactions.
In many European countries the standard rate is 25%.

## Core Concepts

- **Output VAT** — VAT you charge customers (you collect it for the tax authority)
- **Input VAT** — VAT you pay on purchases (you can deduct it)
- **Net amount** — price before VAT
- **Gross amount** — price including VAT
- **VAT payable** = Output VAT - Input VAT (what you owe the government)

## Common VAT Codes

| Code | Rate | When to use |
|------|------|-------------|
| Standard purchase VAT | 25% | Most domestic purchases |
| Standard sales VAT | 25% | Most domestic sales |
| Zero-rated | 0% | Exports, certain services |
| Exempt | None | Financial services, education, healthcare |
| Reverse charge | 0% | Purchases from abroad (you self-assess) |

**Note:** The actual VAT codes vary by accounting system. In e-conomic, check
the VAT accounts via `explore.py --section vat` or `schema.json`.

## Calculating VAT

```
Net amount = 1,000
VAT (25%) = 250
Gross amount = 1,250
```

From gross to net: `Net = Gross / 1.25`
From net to VAT: `VAT = Net * 0.25`

## When VAT Applies

### Domestic purchases (most common)
- Buy goods from a local supplier → standard purchase VAT
- The supplier charges VAT on their invoice
- You record the VAT as input VAT (deductible)

### Domestic sales
- You charge VAT on your invoice
- Record as output VAT (you owe this to tax authorities)

### EU purchases (reverse charge)
- Supplier in another EU country doesn't charge VAT
- You self-assess: record both input AND output VAT
- Net effect is zero, but both must be recorded

### Non-EU purchases
- No VAT on the invoice
- May need to pay import VAT at customs
- Record import VAT as input VAT

### VAT-exempt transactions
- Some services are exempt (financial, medical, educational)
- No VAT charged, no input VAT deductible
- Check with accountant if unsure

## VAT Return Periods

- **Quarterly** — most common for small/medium businesses
- **Monthly** — for larger businesses
- **Annually** — for very small businesses

## For the AI

1. **Default to standard purchase VAT for supplier invoices** unless the context suggests otherwise
2. **Check lessons/rules** — the accountant may have corrected VAT codes before
3. **When unsure, show the VAT code and ask** — "I'm using standard 25% purchase VAT. Is that correct?"
4. **Never guess on reverse charge or exemptions** — ask the user
5. **Separate VAT from the expense** — VAT is always its own line in the entry
