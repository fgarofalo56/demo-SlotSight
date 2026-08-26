---
name: Data model & synthetic generator
description: Schema rules and how the planted narrative signals work
applyTo: "apps/api/src/slotsight/models/**,apps/api/src/slotsight/seed/**"
---

# Data model and the synthetic generator

## Schema rules

**Money is `BigInteger` cents.** Never `Float`, never `Numeric` for money.
Ratios and percentages *are* floats — they are derived, not summed.

**`asset_number` is a natural key** (`NP-21401`), because that is what slot
techs and floor managers say out loud. Format is
`NP-{zone}{bank:02d}{unit:02d}`.

**A bank is the unit of action.** Conversions are executed per bank, never per
machine — a tech does not swap one unit out of an eight-unit bank of the same
title. Any recommendation that does not roll up to a bank is not actionable.

**There is no player table and there never will be.** SlotSight models machines
and money, never people. See `security.instructions.md`.

## The generator produces a story, not noise

`seed/generate.py` is deterministic — same seed, same floor, every time. That
is what lets the golden tests assert on specific conclusions and what lets the
stage demo tell the same story twice.

Four signals are planted (`seed/scenarios.py`):

| Signal | What | Expected conclusion |
|---|---|---|
| 1 | Bank `NP-214` (*Sunset Serpent*) decaying over 60 days | flagged → **convert** |
| 2 | *Neon Tiki Riches* at 1.19 market index, we own none | chosen as **the target** |
| 3 | `NP-10307` reporting ~3.4× par hold | **data quality**, not a star |
| 4 | A zone performing well | explicit **no action** |

**If you change the generator, run `pytest -m golden` immediately.** Those tests
import the constants in `scenarios.py` and assert the pipeline still reaches
each conclusion.

## Tuning traps, learned the hard way

**Widen the distribution and you bury the signal.** `unit_quality` sigma and the
title popularity spread compound. At sigma 0.14 with popularity spanning
0.78–1.28, roughly a fifth of the floor fell below the 0.85 underperformance
threshold on noise alone — which drowned the planted signals and misrepresented
how tightly a real floor clusters. Current values (sigma 0.085, popularity
0.90–1.15) are tuned; change them and re-check the flagged-bank count.

**A cohort coextensive with a zone cannot be benchmarked.** When high-limit
denominations existed *only* in the High Limit zone, that zone's peer group was
itself, its peer index was 1.000 by definition, and Signal 4 could never fire.
`HIGH_LIMIT_DENOM_WEIGHTS` deliberately includes `$1` so the zone shares a
cohort with the main floor.

**Faults dilute as the window widens.** The metering anomaly runs 21 days so it
dominates a 30-day window. Over 90 days the same machine reads below threshold —
correct behaviour, and the reason data-quality checks belong on short windows.

**Reserved titles are placed explicitly, never randomly.** *Sunset Serpent* is
in `RESERVED_TITLES` so it exists on exactly one bank. When random placement
also put it in a healthy zone it surfaced as a **top performer** while the
planted bank was being recommended for conversion — a real and interesting
situation, but a different lesson, and having both at once made neither land.

## The generator is fiction

Every title, manufacturer, and market-data provider is invented. No real
operator data was used, referenced, or reverse-engineered. See
[`../../NOTICE.md`](../../NOTICE.md).
