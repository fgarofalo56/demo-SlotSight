---
name: add-metric
description: Add a new slot-performance metric end to end, the correct way
argument-hint: The metric, e.g. "coin-in per occupied hour"
agent: agent
tools: ['search/codebase', 'search/usages', 'edit/editFiles', 'runCommands', 'slotsight/*']
---

# Add a metric: **${input:metric:Which metric?}**

This prompt exists because there is a **right order** for this in SlotSight, and
doing it out of order produces a metric the assistant can hallucinate.

## The order

### 1. Pure function first — `analytics/metrics.py`

No database, no config, no I/O. Just the arithmetic.

Handle the degenerate cases explicitly and return a value rather than raising:
zero days, zero coin-in, empty cohort, negative win. Across 840 machines these
are normal states, not errors.

### 2. Unit tests — `tests/test_metrics.py`

Cover the happy path **and** every degenerate case. These run in milliseconds
and are the cheapest place to be wrong.

### 3. Wire into aggregation — `analytics/floor.py`

Add it to `MachineMetrics` and populate it in `machine_metrics()`.

⚠️ Coerce Postgres sums with `int()`. `SUM()` over `BIGINT` returns `Decimal`;
mixing it with a `float` raises `TypeError` **only against Postgres**, never in
the SQLite tests.

### 4. Expose on the API — `schemas/` and `routers/`

Add the field to the relevant Pydantic schema and the converter in
`routers/common.py`. Money crosses that boundary as **dollars**; cents stay
inside.

### 5. Only now, give it to the assistant — `agent/tools.py`

Add it to the relevant tool payload, or add a new tool if it answers a genuinely
new question.

**Write the tool description for a reader who does not know the domain.** The
description is the entire basis on which the model decides whether to call it —
a vague description produces a tool that is never used or used wrongly.

### 6. Surface in the UI — `apps/web/`

Format per [`../instructions/react.instructions.md`](../instructions/react.instructions.md).
If it is a performance measure, colour it by **peer index band**, never by the
raw value.

## Then verify

```bash
cd apps/api && uv run ruff check . && uv run mypy src && uv run pytest
cd apps/api && uv run pytest -m golden -v
```

## The rule this prompt enforces

**The assistant may never compute a metric.** It calls a deterministic function
that a test already covers. If you skip steps 1–4 and only add it to the prompt
or the tool payload, you have built something that can produce a number nobody
can reproduce — which is the exact failure this architecture exists to prevent.
