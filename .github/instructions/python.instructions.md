---
name: Python conventions
description: Python style, typing, async, and the money/Decimal gotcha
applyTo: "**/*.py"
---

# Python in SlotSight

Python 3.12+. `ruff` for lint and format (line length 100). `mypy --strict`.

## Typing

Full annotations on every function, including `-> None`. `from __future__ import
annotations` at the top of every module so forward references and modern union
syntax work everywhere.

Prefer `X | None` over `Optional[X]`, `list[X]` over `List[X]`.

## Async

Every I/O path is async. Use `AsyncSession`, `await session.execute(...)`, and
`async with`. Never call a blocking DB or HTTP client from an async function.

## Money — read this before touching a number

**Money is integer cents.** It is stored as `BigInteger`, summed as integers,
and converted to dollars exactly once at the API boundary via
`analytics.metrics.to_dollars`.

Floating-point money accumulates error across a 180-day × 840-machine
aggregation, and slot analytics is exactly the domain where rounding drift
becomes a wrong business recommendation.

⚠️ **The gotcha that will bite you:** Postgres `SUM()` over `BIGINT` returns
`NUMERIC`, which asyncpg hands back as `decimal.Decimal`. Mixing that with a
`float` raises `TypeError`. Coerce at the SQL boundary:

```python
coin_in = int(row.coin_in)          # not row.coin_in
par_hold = float(row.par_hold_pct)
```

This fails **only against Postgres** — the SQLite test suite returns plain
`int` and stays green. See `analytics/floor.py::machine_metrics`.

## Structure

- **Dataclasses** for internal analytics results (`frozen=True` where possible).
- **Pydantic v2** only at the API boundary, in `schemas/`. Use `ConfigDict`,
  `field_validator`, `model_dump` — never the v1 spellings.
- Keep the ORM and the API schema separate. A column rename must not silently
  become a breaking API change.

## Errors

Fail with a message that tells the reader what to *do*, not just what broke.
Compare:

```python
raise RuntimeError("Azure OpenAI not configured")           # useless
raise AzureOpenAINotConfiguredError(missing)                # names the vars,
                                                            # the fix, and what
                                                            # still works
```

Catch narrowly. `except Exception` is acceptable only at a boundary — a CLI
entry point, a health check, or an HTTP handler mapping to a status code — and
must be commented explaining why.

## Comments

Explain **why**, never **what**. A comment restating the code is noise. A
comment explaining a non-obvious trade-off, a domain constraint, or a landmine
is the most valuable line in the file.

Good:
```python
# A cohort smaller than this is not a meaningful benchmark - one unlucky
# machine would swing the average it is being judged against.
MIN_COHORT_SIZE = 6
```

Noise:
```python
# set the minimum cohort size to 6
MIN_COHORT_SIZE = 6
```

## Never

- Add an API-key setting for Azure OpenAI. Auth is Entra ID. There is nothing to
  store.
- Put AI or network calls in `analytics/`.
- Add a player, patron, or loyalty table. This system models machines and money.
