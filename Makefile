# economic-integration Makefile

.PHONY: test lint fetch explore health suggest setup clean

# ── Testing ────────────────────────────────────────────
test:
	python3 -m pytest tests/ -v

test-quick:
	python3 -m pytest tests/ -q

# ── Data pipeline ──────────────────────────────────────
fetch:
	python3 run.py

fetch-year:
	python3 run.py --days 365

explore:
	python3 run.py --explore

schema:
	python3 run.py --schema

health:
	python3 run.py --health

suggest:
	python3 run.py --suggest

# ── Workflows ──────────────────────────────────────────
pl:
	python3 workflows/pl_report.py

pl-quarter:
	python3 workflows/pl_report.py --months 3

overdue:
	python3 workflows/overdue_invoices.py

spend:
	python3 workflows/supplier_spend.py

cashflow:
	python3 workflows/cashflow_check.py

prime-cost:
	python3 workflows/prime_cost.py

monthly:
	python3 workflows/monthly_comparison.py

# ── Knowledge system ───────────────────────────────────
knowledge-show:
	python3 knowledge/loader.py --show

knowledge-lint:
	python3 knowledge/loader.py --lint

knowledge-distill:
	python3 knowledge/loader.py --distill

knowledge-profile:
	python3 knowledge/loader.py --rebuild-profile

knowledge-ingest:
	python3 knowledge/ingest.py

review:
	python3 workflows/review_corrections.py --distill

# ── Setup ──────────────────────────────────────────────
setup:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "\nActivate with: source venv/bin/activate"
	@echo "Then copy .env.example to .env and add your tokens."

# ── Cleanup ────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── Help ───────────────────────────────────────────────
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-quick      Run tests (compact output)"
	@echo ""
	@echo "Data:"
	@echo "  fetch           Fetch last 90 days + ingest"
	@echo "  fetch-year      Fetch full year"
	@echo "  explore         Map your e-conomic setup"
	@echo "  health          Health check + auto-fix"
	@echo ""
	@echo "Reports:"
	@echo "  pl              P&L report (last month)"
	@echo "  pl-quarter      P&L report (last 3 months)"
	@echo "  overdue         Overdue invoices"
	@echo "  spend           Supplier spend analysis"
	@echo "  cashflow        Cash flow check"
	@echo "  prime-cost      Prime cost ratio"
	@echo "  monthly         Month-over-month comparison"
	@echo ""
	@echo "Knowledge:"
	@echo "  knowledge-show     Show knowledge summary"
	@echo "  knowledge-lint     Health check knowledge base"
	@echo "  knowledge-distill  Promote lessons to rules"
	@echo "  review             Review accountant corrections"
	@echo ""
	@echo "Setup:"
	@echo "  setup           Create venv + install deps"
	@echo "  clean           Remove __pycache__ and .pyc files"
