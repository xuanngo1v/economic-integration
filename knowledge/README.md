# Knowledge System

A persistent, compounding knowledge base for AI-assisted bookkeeping.

Inspired by the [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
instead of re-deriving knowledge every session, the AI builds and maintains
a structured knowledge base that grows smarter over time.

## How it works

Three layers:

| Layer | What | Who maintains it | Location |
|-------|------|-------------------|----------|
| **Raw sources** | API data, invoices, entries, explorer reports | Fetched from e-conomic | `data/` |
| **The wiki** | Accounting knowledge, business profile, lessons learned | AI agent | `knowledge/` |
| **The schema** | How the AI should operate, read knowledge, and learn | Human + AI | `LLM.md` |

## Structure

```
knowledge/
├── README.md                    # This file
├── index.md                     # Content catalog — AI reads this first
├── log.md                       # Chronological record of knowledge changes
├── static/                      # Bookkeeping fundamentals (rarely changes)
│   ├── double_entry.md
│   ├── chart_of_accounts.md
│   ├── common_transactions.md
│   ├── vat_rules.md
│   └── compliance.md
├── business/                    # YOUR business (auto-detected + learned)
│   ├── profile.md               # Company setup, account structure, patterns
│   └── preferences.md           # How you want things done
├── lessons/                     # Learning from corrections
│   ├── lessons.json             # Individual corrections captured
│   └── rules.json               # Patterns promoted from repeated lessons
└── loader.py                    # Python module: load relevant knowledge
```

## Operations

### Ingest
When new information arrives (explorer report, accountant correction, user preference),
the AI reads it, extracts key knowledge, and updates the relevant wiki pages.
A single correction might update: `lessons.json`, `preferences.md`, `index.md`, and `log.md`.

### Query
Before acting (creating entries, running reports), the AI reads relevant knowledge pages.
The `index.md` tells it which pages matter for the current task.

### Lint
Periodically, check the knowledge base for:
- Contradictions between lessons and static knowledge
- Stale business profile (accounts changed since last explore)
- Lessons that should be promoted to rules (3+ similar corrections)
- Gaps: common transaction types not yet documented in lessons

## The learning loop

```
AI proposes draft entry
    ↓
Accountant reviews in e-conomic
    ↓
If corrected → AI captures the diff as a lesson
    ↓
Lesson stored with: what changed, context, reason (if known)
    ↓
After 3+ similar lessons → promoted to a rule
    ↓
Next time → AI checks rules first → gets it right
```

## For AI agents

1. At session start, read `knowledge/index.md` to see what knowledge exists
2. Before any write operation, call `load_knowledge(task_type)` from `loader.py`
3. After a correction is detected, call `add_lesson()` to capture it
4. Periodically run `python knowledge/loader.py --lint` to health-check

## Principles

- **Knowledge compounds** — every correction makes the system smarter
- **The AI maintains the wiki** — humans curate and verify
- **Adapt to the business** — no two businesses use the same accounts the same way
- **Static knowledge is the floor** — lessons and rules are the ceiling
- **Log everything** — the timeline of how knowledge evolved is itself knowledge
