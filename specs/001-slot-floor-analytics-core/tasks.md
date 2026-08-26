# Tasks — 001 Slot floor analytics core

All complete. Kept in place as the worked example of what a finished task list
looks like — including the two tasks that were added *during* implementation,
which is the normal and honest case.

---

- [x] **T1 — Pure metric functions**
      Files: `analytics/metrics.py`
      Done when: WPUPD, hold %, index, hold deviation, trend slope, and
      `peer_cohort_key` exist with no imports beyond the standard library.
      Verify: `uv run pytest tests/test_metrics.py -v`

- [x] **T2 — Metric unit tests**
      Files: `tests/test_metrics.py`
      Done when: every function has a happy-path test and a degenerate-case
      test (zero days, zero coin-in, empty cohort, negative win).
      Verify: `uv run pytest tests/test_metrics.py -v` — 28 passed

- [x] **T3 — ORM models**
      Files: `models/__init__.py`
      Done when: zones, machines, daily_performance, market_titles, and
      competitor_offerings exist; money is `BigInteger`; **there is no player
      table**; the composite index leads with `asset_number`.
      Verify: `uv run mypy src`

- [x] **T4 — Async database layer**
      Files: `db.py`, `config.py`
      Done when: engine, session factory, and FastAPI dependency exist and
      `create_all()` succeeds against Postgres.
      Verify: `docker compose up -d db && slotsight-seed --reset`

- [x] **T5 — Synthetic generator**
      Files: `seed/catalog.py`, `seed/scenarios.py`, `seed/generate.py`
      Done when: 840 machines × 180 days generate deterministically and all
      four planted signals are present at the expected magnitudes.
      Verify: `slotsight-seed --reset` then inspect the four signals

- [x] **T6 — The core aggregation query**
      Files: `analytics/floor.py`
      Done when: `machine_metrics()` returns per-machine totals with peer and
      floor indices, cohort size, and the `MIN_COHORT_SIZE` fallback.
      Verify: `uv run pytest tests/test_api.py -k index`

- [x] **T7 — Outlier detection**
      Files: `analytics/outliers.py`
      Done when: underperformers are confirmed against a prior window and
      carry `sustained`; data-quality flags are computed first and their
      subjects are excluded from **both** performance lists.
      Verify: `uv run pytest -m golden -v`

- [x] **T8 — Bank rollup**
      Files: `analytics/outliers.py`
      Done when: findings aggregate to bank level and are reported only when
      ≥50% of a bank's units are flagged.
      Verify: `uv run pytest -m golden -k rolls_up`

- [x] **T9 — HTTP surface**
      Files: `routers/`, `schemas/`, `main.py`
      Done when: floor, machines, recommendations, outliers, and market
      endpoints return typed responses; money crosses the boundary as dollars.
      Verify: `curl -fsS localhost:8000/api/floor/summary`

- [x] **T10 — Golden tests**
      Files: `tests/test_scenarios.py`
      Done when: each of the four planted signals has a test asserting the
      **conclusion**, not just the return value.
      Verify: `uv run pytest -m golden -v` — 18 passed

---

## Added during implementation

Both discovered by running the thing. Neither was anticipated by the plan.

- [x] **T11 — Coerce Postgres `Decimal` at the SQL boundary** *(added T6+1)*
      Files: `analytics/floor.py`
      Why: `SUM()` over `BIGINT` returns `NUMERIC`, which asyncpg hands back as
      `decimal.Decimal`. Dividing it by a float par raised `TypeError` — and
      **only against Postgres**; the SQLite suite was green throughout.
      Done when: sums are `int()`-coerced with a comment explaining the trap.
      Verify: pipeline runs clean against Postgres

- [x] **T12 — Give High Limit a shared denomination cohort** *(added T7+1)*
      Files: `seed/catalog.py`, `seed/generate.py`
      Why: high-limit denominations existed only in the High Limit zone, so its
      peer group was itself, its index was 1.000 by definition, and the
      healthy-zone signal could never fire. Real high-limit rooms carry $1
      units; adding them fixed the model and the realism together.
      Done when: `HIGH_LIMIT_DENOM_WEIGHTS` includes `$1` and the zone indexes
      above 1.05 against true peers.
      Verify: `uv run pytest -m golden -k healthy_zone`
