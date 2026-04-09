# Contributing to Ledger Pilot

Thanks for your interest in contributing! This project is open to anyone who wants to improve AI-assisted bookkeeping.

## Ways to contribute

### Add support for a new accounting platform

The biggest contribution opportunity. The core architecture is API-agnostic — only two files are e-conomic specific:

- `api.py` — API authentication and HTTP helpers
- `fetch.py` — Data fetching from the accounting API

To add a new platform (Xero, QuickBooks, Dinero, Billy, etc.):

1. Fork the repo
2. Create a new branch: `git checkout -b add-xero-support`
3. Implement your own `api.py` and `fetch.py` for the new platform
4. Update `account_map.py` if the platform uses different account structures
5. Test with `make test`
6. Submit a PR

Everything else (knowledge system, workflows, learning loop) should work as-is.

### Add a new workflow

Workflows live in `workflows/`. To add one:

1. Copy `workflows/TEMPLATE.py` to a new file
2. Implement your analysis or action
3. Follow the existing patterns (use `api.py` for API calls, `account_map.py` for categorization)
4. Add a test in `tests/` if applicable
5. Submit a PR

### Improve the knowledge system

The `knowledge/` folder contains bookkeeping fundamentals. Contributions welcome for:

- Fixing or expanding static knowledge files
- Adding knowledge for specific industries or jurisdictions
- Improving the learning loop (better correction detection, smarter distillation)

### Report bugs or suggest features

Open an issue on GitHub. Include:

- What you expected to happen
- What actually happened
- Steps to reproduce (if applicable)

## Development setup

```bash
git clone https://github.com/xuanngo1v/ledger-pilot.git
cd ledger-pilot
make setup              # Creates venv + installs deps
make test               # Run tests (should all pass)
```

## Code style

- Follow existing patterns — look at how other files are structured
- Import from `api.py` for API calls (don't add your own `_headers()` or `_get_all()`)
- Import from `account_map.py` for categorization (single source of truth)
- Keep workflows self-contained — one file, one purpose
- No hardcoded business data — the system adapts to each user's setup

## Pull request guidelines

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- Make sure `make test` passes
- Update documentation if your change affects how things work

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
