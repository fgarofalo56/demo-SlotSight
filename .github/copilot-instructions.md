# SlotSight — repository instructions for GitHub Copilot

You are working in **SlotSight**, an AI-assisted slot floor performance analyst for
the fictional **Neon Palms Casino Resort**.

This repository is a teaching reference for **spec-driven development**. The
application is real and works; it exists so the *process* that built it has
something to point at.

---

## 🚨 The five rules

These are not style preferences. Breaking one is a defect.

### 1. Never commit a secret or any PII

No credential, key, token, connection string, or personal data in code, config,
tests, fixtures, or commit messages. Not temporarily. `.env` is gitignored;
`.env.example` holds placeholders only and is the sole tracked `.env*`.

Azure OpenAI uses **Entra ID via `DefaultAzureCredential`** — there is no
API-key setting anywhere and you must not add one.

This repo has **no player data by design**: no names, loyalty IDs, card numbers,
or session tracking. It models machines and money, never people. Adding PII is a
defect, not a feature. See [SECURITY.md](../SECURITY.md).

### 2. The analytics stay deterministic and LLM-free

`apps/api/src/slotsight/analytics/` contains **no AI and no network calls**.
Every conclusion SlotSight reaches is produced there, by ordinary code, against
ordinary SQL, covered by ordinary tests.

`slotsight/agent/` is a presentation shell. It may reach data **only** through
functions in `analytics/`. It must never write its own query, and it must never
compute a figure itself. That constraint is what makes every number the
assistant says auditable.

If you are asked to "make the AI smarter", the answer is almost always a better
deterministic function plus a better tool description — not a longer prompt.

### 3. Money is integer cents; ratios are floats

Money is stored, summed, and passed around as **integer cents**. It converts to
dollars exactly once, at the API boundary (`analytics/metrics.py::to_dollars`).
Floating-point money accumulates error across a 180-day × 840-machine
aggregation, and this is precisely the domain where a rounding drift becomes a
wrong business recommendation.

⚠️ Postgres `SUM()` over `BIGINT` returns `NUMERIC`, which asyncpg gives you as
`decimal.Decimal`. Coerce with `int()` at the SQL boundary. Mixing `Decimal` and
`float` raises `TypeError` — and only against Postgres, never in the SQLite
tests.

### 4. Compare machines to peers, not to the floor

**The single most important judgement call in the codebase.**

A machine's `peer_index` compares it to the same *(denomination, game type)*.
Its `floor_index` compares it to everything. Floor-wide indexing mostly just
sorts by denomination — it makes every penny machine look like a removal
candidate and every $5 machine look like a star.

In this dataset the High Limit zone reads **3.4× on floor index** and **1.07× on
peer index**. Only the second number is actionable. Both are returned so the UI
can show the difference; never rank or recommend on `floor_index`.

### 5. Every feature starts as a spec

Non-trivial work follows `specs/NNN-name/`: `spec.md` → `plan.md` → `tasks.md` →
implementation → verification. Use the `/spec-*` prompt files. Do not start
writing code for a new capability that has no spec — write the spec first, or
ask for one.

---

## 🗺️ Where things are

```
apps/api/src/slotsight/
  config.py       env-driven settings; no credential defaults
  db.py           async engine + session
  models/         SQLAlchemy ORM (integer cents, no player table)
  analytics/      ← THE CORE. deterministic, LLM-free, fully tested
    metrics.py      pure functions: WPUPD, hold, peer indexing
    floor.py        the one aggregation query everything builds on
    outliers.py     underperformers, top performers, bad data
    recommend.py    actions with evidence attached
  market/         pluggable market-intel adapter (synthetic only)
  agent/          Azure OpenAI tool-calling shell over analytics/
  routers/        HTTP surface
  seed/           synthetic generator + the planted narrative signals
apps/web/         React 19 + Vite + TS + Tailwind (Neon Palms theme)
mcp/              our own MCP server exposing the analytics to Copilot
infra/            Bicep for azd
specs/            the spec-driven development artifacts
```

## 🧪 Gates

Nothing is "done" until these pass and you have shown the output.

```bash
make gates      # everything below

cd apps/api && uv run ruff check . && uv run mypy src && uv run pytest
cd apps/web && pnpm exec tsc --noEmit && pnpm test && pnpm build
```

The tests marked `golden` are the ones that matter most:

```bash
uv run pytest -m golden -v
```

They do not assert that a function returns a number. They assert the pipeline
reaches the **right conclusion** about a floor whose truth we control — see
`slotsight/seed/scenarios.py`. Break the analytics and they fail even when every
unit test still passes.

## 🎰 Domain vocabulary

| Term | Meaning |
|---|---|
| **Coin-in** | Total wagered. *Not* revenue — one $20 recycled 30× is $600 of coin-in. |
| **Theo win** | What the game should win at its paytable: `coin_in × par_hold_pct`. |
| **Actual win** | What it did win. Diverges from theo by short-run variance. |
| **Hold %** | `actual_win / coin_in`. The realized take. |
| **Par hold** | The hold the paytable is *designed* for. A property of the game. |
| **WPUPD** | Win Per Unit Per Day. The headline metric. |
| **Bank** | Physically adjacent units, same title. **Conversions happen per bank.** |
| **Peer index** | WPUPD ÷ average WPUPD of the same denom + game type. |

Longer version: [`docs/slot-analytics-primer.md`](../docs/slot-analytics-primer.md).

## ✍️ Conventions

**Python** — 3.12+, full type hints, `ruff` (line length 100), `mypy --strict`.
Async everywhere for I/O. Pydantic v2 (`ConfigDict`, `field_validator`,
`model_dump` — never the v1 spellings). Dataclasses for internal analytics
results, Pydantic only at the API boundary.

**TypeScript** — strict mode, no `any`, no non-null `!`. Function components
with hooks. Tailwind utility classes; the Neon Palms tokens live in
`apps/web/src/theme/`.

**Comments** explain *why*, never *what*. A comment restating the code is noise;
a comment explaining a non-obvious trade-off is the most valuable line in the
file.

**Tests** are named for the behaviour they protect, not the function they call.
`test_anomaly_is_excluded_from_top_performers` beats `test_find_top_performers_2`.

## 🎭 Everything is fictional

The casino, the game titles, the manufacturers, and the market-data providers
are all invented. The market-intel layer is a pluggable interface with exactly
one **synthetic** implementation — no scraping, no vendor API, no affiliation.

Any response carrying market data must set `is_synthetic: true` and a
disclaimer. A recommendation built on invented benchmarks must never reach a
screen looking like one built on real market intelligence. See
[NOTICE.md](../NOTICE.md).

## 🤖 What to reach for

- **Azure/Bicep/deployment questions** → `microsoft-docs` MCP server, then `azure`
- **Library APIs** (FastAPI, SQLAlchemy, React, Tailwind) → `context7` MCP server
- **Live floor data while you work** → `slotsight` MCP server (our own)
- **Issues/PRs** → `github` MCP server

Custom agents live in `.github/agents/`. Reach for `spec-architect` to start a
feature, `implementer` to build one, `code-reviewer` before merging.
