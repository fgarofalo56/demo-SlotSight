---
name: slot-floor-analytics
description: Casino slot floor performance analysis — WPUPD, hold, par, peer indexing, and the reasoning traps that make naive analysis wrong. Use when working on anything in analytics/, interpreting floor numbers, adding a metric, or answering a question about machine performance.
---

# Slot floor analytics

Domain knowledge for reasoning about slot machine performance correctly.

## The vocabulary

| Term | Meaning | The trap |
|---|---|---|
| **Coin-in** | Total amount wagered | **Not revenue.** One $20 bill recycled thirty times is $600 of coin-in. |
| **Handle pulls** | Number of spins | A penny slot bet is ~75¢ across 50–88 lines, not one cent |
| **Theo win** | `coin_in × par_hold_pct` | What the game *should* win |
| **Actual win** | What it did win | Diverges from theo by variance — that gap is not performance |
| **Hold %** | `actual_win / coin_in` | Realized, not designed |
| **Par hold** | What the paytable is set to | A property of the *game*, not of its performance |
| **WPUPD** | Win Per Unit Per Day | The headline metric |
| **Bank** | Adjacent units, same title | **Conversions happen per bank**, never per machine |
| **Peer index** | WPUPD ÷ cohort average | 1.00 = average. The actionable number. |
| **Floor index** | WPUPD ÷ floor average | Mostly just sorts by denomination |

## Formulas

```
hold_pct        = actual_win_cents / coin_in_cents
theo_win        = coin_in_cents × par_hold_pct
wpupd           = actual_win_cents / days / 100          → dollars
peer_index      = machine_wpupd / cohort_mean_wpupd
hold_deviation  = observed_hold / par_hold               → ~1.0 is healthy
```

Cohort = **(denomination, game_type)**.

---

## The four traps

Each of these is a real way to be confidently wrong.

### 1. Benchmarking against the floor average

The obvious approach and the wrong one. A $5 machine will always out-earn a
penny machine, so a floor-wide index mostly re-renders the denomination column
as a ratio.

In this dataset High Limit reads **3.44 on floor index** and **1.07 on peer
index** — the same fifty machines. The first number would make every penny
machine a removal candidate.

**Always compare within (denomination, game type).**

### 2. Treating one weak window as evidence

Slot results are genuinely volatile in the short run. A machine can trail its
peers for three weeks on variance alone, and converting it produces a change
that reverts to the mean — which then destroys confidence in the whole analysis.

Confirm against a prior window. Respect the `sustained` flag. Unsustained means
*watch*, not *act*.

### 3. Believing a machine that holds far above par

Sustained hold several times the paytable par is a bill validator fault, a meter
rollover, or a miskeyed par. **It is never a great machine.**

On a rank-by-win leaderboard this machine is first, and someone orders eight more
of a broken unit. An analytics tool that cannot say *"I don't believe this
number"* is not safe to act on.

Flag it, and exclude it from rankings in **both** directions.

### 4. Blaming the game when the problem is the position

A bank far below its cohort in an otherwise healthy zone is a game problem. A
whole row that is weak is a floor-position problem, and converting the title will
not fix it.

**Check the neighbours before recommending a conversion.**

---

## Reasoning about a conversion

A conversion is a **hypothesis**, not a conclusion. Before recommending one:

1. Is the decline **sustained** across two windows?
2. Is it the **bank**, or one unit? (One unit is a service call.)
3. Are the **neighbours** also weak? (Then it is the position.)
4. Is the target **compatible** — same denomination, same game type? Otherwise
   it is a purchase, not a conversion, and a different budget line.
5. Does the target beat the incumbent by enough to repay the **downtime**?
6. What is the **measurement plan**? 30 days post-install against the same peer
   cohort.

Impact estimates in this codebase assume only **half** the observed market edge
transfers to this floor (`TRANSFER_COEFFICIENT`). Different demographic,
different position, different competitive set. Say the estimate is an estimate.

## When a cohort is too small

Below `MIN_COHORT_SIZE` (6), one unlucky machine swings the average it is being
judged against. The code falls back to the floor average and surfaces
`peer_cohort_size` so a caller can see the benchmark is thin. Say so when you
cite it.

## Denominations

| Cents | Name | Typical daily coin-in | Typical par hold |
|---:|---|---:|---:|
| 1 | Penny | ~$2,450 | 8.3–11.8% |
| 5 | Nickel | ~$2,100 | 7.0–9.5% |
| 25 | Quarter | ~$3,150 | 6.0–8.2% |
| 100 | Dollar | ~$4,900 | 4.8–6.8% |
| 500 | $5 | ~$16,800 | 3.8–5.2% |

Higher denomination → **higher coin-in, lower hold**. Video poker runs far more
coin-in at roughly a third the hold of a reel game — which is why it needs its
own cohort.

---

## Where this lives in the code

| File | What |
|---|---|
| `analytics/metrics.py` | The formulas, as pure functions |
| `analytics/floor.py` | The one aggregation query + peer indexing |
| `analytics/outliers.py` | Traps 2 and 3, encoded |
| `analytics/recommend.py` | The conversion checklist, encoded |
| `seed/scenarios.py` | Four planted signals the tests assert against |

Longer prose version: [`docs/slot-analytics-primer.md`](../../../docs/slot-analytics-primer.md)

> All data in this repository is synthetic. See [`NOTICE.md`](../../../NOTICE.md).
