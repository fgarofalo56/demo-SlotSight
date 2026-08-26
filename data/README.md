# Data

**The generator lives at
[`apps/api/src/slotsight/seed/`](../apps/api/src/slotsight/seed/).**

It is inside the API package deliberately: it writes through the same SQLAlchemy
models the application reads, so it cannot drift from the schema, it ships in
the same container, and the golden tests can import its planted-signal constants
directly.

| File | Holds |
|---|---|
| `catalog.py` | Fictional zones, manufacturers, titles, denominations |
| `scenarios.py` | **The four planted narrative signals** |
| `generate.py` | The generator itself |

## Running it

```bash
make seed          # generate if empty
make reseed        # drop and regenerate
```

Standalone:

```bash
uv run --project apps/api slotsight-seed --reset
```

Produces **840 machines × 180 days = 151,200 rows** in 10–15 seconds, plus a
synthetic market feed and competitor sightings.

## Deterministic on purpose

Same seed, same floor, every time. That is what lets the golden tests assert on
specific conclusions and what lets a stage demo tell the same story twice.

Change `SEED_RANDOM_SEED` and the planted signals move — and
`apps/api/tests/test_scenarios.py` will fail. **That is intentional.**

## The four planted signals

| Signal | Planted | The analytics must conclude |
|---|---|---|
| 1 | Bank `NP-214` decaying over 60 days | flagged → **convert** |
| 2 | *Neon Tiki Riches* at 1.19 market index, we own none | chosen as **the target** |
| 3 | `NP-10307` reporting ~2.7× par hold | **bad data**, not a star |
| 4 | A zone performing well | explicit **no action** |

Read [`scenarios.py`](../apps/api/src/slotsight/seed/scenarios.py) — it explains
each one and why it is there.

---

> ⚠️ Every number produced here is invented. No real operator data was used,
> referenced, or reverse-engineered. See [`NOTICE.md`](../NOTICE.md).
