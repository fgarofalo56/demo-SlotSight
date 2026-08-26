---
name: Testing conventions
description: How to write tests that protect behaviour, including golden tests
applyTo: "**/tests/**,**/*.test.ts,**/*.test.tsx,**/*.spec.ts"
---

# Testing in SlotSight

## Name tests for the behaviour they protect

The test name is documentation that runs. It should say what breaks if the test
fails.

```python
def test_anomaly_is_excluded_from_top_performers(): ...   # ✅ names the risk
def test_find_top_performers_2(): ...                     # ❌ names nothing
```

## The three tiers

**Unit** (`test_metrics.py`) — pure functions, no database, milliseconds. If the
arithmetic is wrong everything downstream is wrong, and these find it instantly.

**Integration** (`test_api.py`) — HTTP contract against a seeded in-memory
database. Covers the shapes the frontend and MCP server depend on.

**Golden** (`test_scenarios.py`, marked `@pytest.mark.golden`) — the ones that
matter most, and a genuinely different kind of test.

## Golden tests: assert conclusions, not return values

The synthetic dataset has **four narrative signals deliberately planted in it**
(`slotsight/seed/scenarios.py`). Golden tests assert the pipeline reaches the
right *conclusion* about a floor whose truth we control:

- the declining bank is flagged **and recommended for conversion**
- the hot market title is **chosen as the target**
- the metering fault is flagged as bad data and **kept out of the leaderboard**
- a healthy zone is **explicitly reported as needing no action**

That makes the dataset the test oracle. Refactor the analytics, move a
threshold, or "optimize" a query in a way that breaks the conclusions and these
fail — even when every unit test still passes.

**When you change the analytics, run these first:**

```bash
uv run pytest -m golden -v
```

If a golden test fails, do not adjust the assertion to match the new output.
Work out which behaviour changed and whether that was intended. The whole
purpose of these tests is that they are hard to silence.

## Anchor windows to the data, not the clock

Use the `analysis_end_date` fixture. Tests anchored on `date.today()` start
failing the moment the machine clock rolls past the fixture's range — a failure
that arrives at midnight, on someone else's machine, for no reason.

## Test the failure modes people actually hit

The single most valuable API test in this repo asserts that `/api/chat` returns
a **503 with actionable remediation** when Azure OpenAI is not configured, and
that the analytics endpoints keep working. That is the first thing a new cloner
will experience.

## Do not

- Assert on exact floating-point equality — use `pytest.approx`.
- Mock the analytics layer in API tests. It is fast, deterministic, and mocking
  it would test the mock.
- Add a test that needs network access without marking it `requires_azure`.
- Put a real credential in a fixture. Ever.
