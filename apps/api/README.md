# SlotSight API

FastAPI backend for **SlotSight** — the slot floor performance assistant for the
fictional Neon Palms Casino Resort.

> ⚠ All data is synthetic. See [`NOTICE.md`](../../NOTICE.md) at the repo root.

---

## Architecture in one sentence

**The analytics are deterministic SQL; the LLM only phrases the answer.**

```
routers/  →  analytics/   ← deterministic, LLM-free, fully unit-tested
             ↑
   agent/  ──┘             ← Azure OpenAI tool-calling; calls analytics, never SQL
```

This split is the architectural point of the whole demo. `agent/` may **only**
reach the data through the same functions `routers/` uses. It never writes its
own query. The consequence: every number in a chat answer is one a test already
covers, and the model cannot invent a figure even if it tries.

## Layout

| Path | Purpose |
|---|---|
| `src/slotsight/config.py` | Environment-driven settings. No credential defaults. |
| `src/slotsight/db.py` | Async engine, session factory, FastAPI dependency |
| `src/slotsight/models/` | SQLAlchemy ORM. Money is integer cents; there is no player table. |
| `src/slotsight/analytics/` | **The core.** WPUPD, peer indexing, outliers, recommendations. |
| `src/slotsight/agent/` | Azure OpenAI tool-calling shell over `analytics/` |
| `src/slotsight/market/` | Pluggable market-intel adapter (synthetic implementation only) |
| `src/slotsight/routers/` | HTTP surface |
| `src/slotsight/seed/` | Synthetic floor generator + the planted narrative signals |
| `tests/` | Unit tests + golden tests asserting the planted signals |

## Running it

From the **repository root**, not here:

```bash
docker compose up --build     # everything
make seed                     # regenerate the synthetic floor
```

Standalone, against a Postgres you already have:

```bash
uv venv && uv pip install -e ".[dev]"
uv run slotsight-seed --reset
uv run uvicorn slotsight.main:app --reload
```

## Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

The `golden` marker covers the four planted signals:

```bash
uv run pytest -m golden -v
```

These are the tests that matter most. They don't assert that a function
returns a number — they assert the pipeline reaches the right *conclusion*
about a floor whose truth we control. Break the analytics and they fail.

## Azure OpenAI

Required for `/api/chat` **only**. Everything else is deterministic SQL and
runs with no cloud dependency at all.

Auth is **Entra ID via `DefaultAzureCredential`** — there is no API-key setting,
so there is no key to leak. Run `az login` and make sure your account holds
`Cognitive Services OpenAI User` on the resource.

`GET /api/health` reports whether Azure OpenAI is **configured**, without
revealing the endpoint or any token. It deliberately reports `"configured"`
rather than `"ok"` — two environment variables being set does not prove the
credential resolves. `POST /api/chat` is the only real check.
