# 001 — Slot floor analytics core

**Status:** Implemented
**Created:** 2026-08-20
**Completed:** 2026-08-24

---

## Problem

Slot floor performance analysis at Neon Palms is manual, reactive, and
fragmented. Identifying which machines are underperforming means exporting
meter data, building a pivot in a spreadsheet, and eyeballing it — a process
that takes a slot analyst most of a morning and produces a different answer
depending on who ran it.

Three specific failures recur:

1. **Comparisons are made against the wrong baseline.** The floor-wide average
   is the obvious reference, and it is wrong: it mostly sorts by denomination,
   making every penny machine look weak and every high-limit machine look
   strong.
2. **One bad week gets treated as evidence.** Slot results are volatile in the
   short run. Acting on a single weak window produces conversions that revert
   to the mean and destroy confidence in the analysis.
3. **Bad data is treated as good performance.** A machine with a metering fault
   reports an implausibly high hold and rises to the top of any
   rank-by-win report.

## Users

- **Slot floor manager** — needs to know which banks to act on this week
- **Slot analyst** — needs the numbers to be defensible in a meeting
- **Director of slot operations** — needs to know the floor is healthy without
  reading a spreadsheet

## Desired outcome

A deterministic analytics layer that, given the property's daily meter data,
identifies underperforming machines against a defensible baseline, distinguishes
sustained decline from short-run variance, and refuses to rank machines whose
data it does not trust.

## Acceptance criteria

1. Per-machine metrics are computed over an arbitrary trailing window: WPUPD,
   coin-in per day, realized hold %, and hold deviation from paytable par.
2. Every machine carries a **peer index** benchmarking it against machines of
   the same denomination and game type, and a **floor index** against the whole
   floor. Both are returned; only peer index is used for ranking.
3. A cohort smaller than 6 units falls back to the floor average, and the
   cohort size is surfaced so a caller can see the benchmark is thin.
4. Underperformance is only reported when confirmed against a prior window of
   equal length, or when the index is falling by at least 0.08 between windows.
   The result carries a `sustained` flag.
5. Machines whose realized hold deviates from par by ≥2.0× (or ≤0.25×) are
   flagged as data-quality issues and **excluded from both the top-performer
   and underperformer lists**.
6. Machines with under $150/day of coin-in are not evaluated for hold
   deviation, because the ratio is noise at that volume.
7. Findings roll up to **bank** level, reported only when at least half a
   bank's units are flagged.
8. All money is integer cents internally and dollars at the API boundary.
9. Every metric function handles its degenerate cases (zero days, zero coin-in,
   empty cohort, negative win) by returning a value rather than raising.
10. The full pipeline runs against 840 machines × 180 days in under 2 seconds
    for a 30-day window.

## Out of scope

- Market/competitor data — spec 002 and 003
- Natural-language querying — spec 002
- Any recommendation of *what to convert to* — needs market data (spec 002)
- Player-level analysis — permanently out of scope, see Constitution VII
- Real-time or intraday data; this is a daily-grain system

## Open questions

*(All resolved during `/spec-clarify`.)*

- ~~Should the peer cohort include zone?~~ **Resolved:** no. Zone is a
  *finding*, not a control — if a whole zone underperforms its cross-floor
  cohort, that is the interesting result and folding zone into the cohort would
  hide it.
- ~~What threshold defines underperformance?~~ **Resolved:** peer index ≤ 0.85,
  chosen so roughly 10–20% of a realistic floor is flagged. Below that it
  misses real decline; above it, the list becomes noise.
- ~~How long a confirmation window?~~ **Resolved:** the immediately preceding
  window of equal length. Simple to explain to an operator, which matters more
  than statistical elegance here.

## Constraints

Bound by the [Constitution](../../.specify/memory/constitution.md):

- **I** — no AI, no network calls anywhere in this layer
- **III** — rank on peer index, never floor index
- **V** — data-quality findings evaluated first and excluded from rankings
- **VI** — money is integer cents
- **VII** — no player data

---

## Verification

| Criterion | Status | Evidence |
|---|---|---|
| 1 | ✅ | `analytics/metrics.py`, `tests/test_metrics.py` (28 tests) |
| 2 | ✅ | `floor.py::machine_metrics`, `test_api.py::test_summary_returns_both_indices` |
| 3 | ✅ | `MIN_COHORT_SIZE`, `peer_cohort_size` on every result |
| 4 | ✅ | `outliers.py::find_underperformers`, `test_decline_is_detected_as_sustained` |
| 5 | ✅ | `detect_data_quality`, `test_anomaly_is_excluded_from_top_performers` |
| 6 | ✅ | `MIN_COIN_IN_PER_DAY_DOLLARS` |
| 7 | ✅ | `rollup_to_banks`, `test_bank_rolls_up_as_a_unit` |
| 8 | ✅ | `BigInteger` columns; `to_dollars` called once, in `routers/common.py` |
| 9 | ✅ | `test_metrics.py` — every function has a degenerate-case test |
| 10 | ✅ | Full suite (68 tests incl. seeding 151k rows) runs in ~11 s |

**Gates run 2026-08-24:** `ruff check` clean · `mypy src` clean ·
`pytest` 68 passed · `pytest -m golden` 18 passed.

## What we learned

**The peer-cohort decision was the whole spec.** Everything else followed from
it. It is also the thing most likely to be "simplified" by someone who does not
know the domain, which is why it has its own long comment in
`metrics.py::peer_cohort_key` and its own test.

**A cohort coextensive with a zone cannot be benchmarked.** High-limit
denominations initially existed only in the High Limit zone, so that zone's
peer group was itself and its index was 1.000 by definition. Fixed by giving
the salon a share of $1 units — which is also how real high-limit rooms are laid
out. Not something the spec anticipated.
