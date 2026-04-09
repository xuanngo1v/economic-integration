# Compliance Basics

Legal requirements for bookkeeping. These rules exist to ensure
businesses maintain accurate, verifiable financial records.

## Core Requirements

### 1. Record Retention
- All financial records must be kept for **5 years** after the fiscal year ends
- This includes: invoices, receipts, bank statements, journal entries, annual reports
- Digital records are acceptable (and often required)
- The records must be accessible and readable for the full retention period

### 2. Audit Trail
- Every transaction must be traceable from the financial statement back to the source document
- Journal entries must have: date, accounts, amounts, description, and reference
- Deleted or modified entries must leave a trace (no silent edits)
- This is why e-conomic separates "draft" from "booked" — booked entries can't be silently changed

### 3. Digital Bookkeeping
- Modern bookkeeping laws require digital record-keeping systems
- The system must be able to produce reports on demand
- Data must be stored in a recognized format
- Backups are required

### 4. Fiscal Year
- Typically 12 months, often aligned with the calendar year (Jan-Dec)
- Can be offset (e.g. Apr-Mar) — check the company's setup
- Year-end closing must happen within a set timeframe after the fiscal year ends
- The annual report must be filed with the business authority

## Separation of Duties

- The person who creates entries should not be the same person who approves them
- This is why the project uses a "draft → accountant review → book" workflow
- The AI creates drafts. The accountant books them. This is correct separation.

## What the AI Must Never Do

1. **Never book entries directly** — only create drafts and vouchers
2. **Never delete financial records** — append corrections, don't erase
3. **Never bypass the accountant** — all write operations need human approval
4. **Never fabricate documentation** — if there's no source document, don't create an entry
5. **Never modify booked entries** — if a booked entry is wrong, create a reversal

## What the AI Should Do

1. **Always log actions** — every entry created, every report run
2. **Always show previews** — let the user see what will be created before confirming
3. **Always include descriptions** — entries without descriptions fail audits
4. **Flag unusual amounts** — if an entry is 10x normal, ask before proceeding
5. **Maintain the learning loop** — capture corrections to improve over time

## Common Deadlines

Deadlines vary by jurisdiction and company size. The accountant knows the
specific deadlines. The AI should:
- Track when VAT returns are due (quarterly or monthly)
- Remind about year-end closing requirements
- Note payroll deadlines (monthly)
- Flag annual report filing deadlines
