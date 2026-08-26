# 🎰 Slot analytics primer

For readers who have never worked a casino floor. Everything you need to
understand what SlotSight is doing and why the obvious approach is wrong.

> All numbers below come from this repository's **synthetic** dataset. See
> [`NOTICE.md`](../NOTICE.md).

---

## The vocabulary

**Coin-in** — the total amount wagered. **This is not revenue.** A guest who
puts in $20 and plays it through thirty times generates $600 of coin-in from
$20 of actual money. It measures activity, not income.

**Handle pulls** — the number of spins. Note that a "penny" slot is not a
one-cent bet: a typical wager is 50–88 lines at a penny each, so around 75¢ per
spin.

**Par hold** — the percentage of coin-in the game is *designed* to keep, set by
its paytable. A property of the game, fixed at manufacture. An 8.75% par means
that over millions of spins the machine keeps 8.75 cents per dollar wagered.

**Theo win** — `coin_in × par_hold`. What the machine *should* have won.

**Actual win** — what it did win. Diverges from theo by short-run variance.
**That gap is luck, not performance.**

**Hold %** — `actual_win / coin_in`. The realized take. Converges on par over
time, wanders far from it over a week.

**WPUPD** — Win Per Unit Per Day. `actual_win / days`. The headline metric.
Normalizing by days is what makes a machine installed three weeks ago comparable
to one installed three years ago.

**Bank** — a physically adjacent group of machines, usually the same title.
**Conversions happen per bank.** Nobody swaps one unit out of an eight-unit bank
of the same game.

---

## The question, and the trap

The question is: *which machines are underperforming?*

The obvious method is to compute WPUPD for every machine and rank it. Here is
what that produces on this floor:

| Machine | Denomination | WPUPD |
|---|---|---:|
| High Limit unit | $5 | $875 |
| Main floor unit | Penny | $238 |
| Bar top unit | Penny | $197 |

The $5 machine earns 3.7× the penny machine. **So what?** It costs more to play.
That ranking has told you the denomination column, in a different font.

Do this at scale and every penny machine looks like a removal candidate — which
would empty the most profitable square footage on the floor, since penny games
are where the volume is.

---

## Peer indexing

Compare a machine to **machines competing for the same guest and the same square
footage**: same denomination, same game type.

```
peer_index = machine_wpupd / mean_wpupd_of_same_denom_and_game_type
```

`1.00` is exactly average for its cohort. `0.80` is 20% below.

The difference on this floor:

| Zone | Floor index | Peer index |
|---|---:|---:|
| Main Floor North | 0.94 | **1.13** |
| High Limit Salon | **3.44** | **1.07** |
| Main Floor South | 0.79 | 0.94 |
| Sunset Bar Tops | 0.77 | 0.87 |

Floor index says High Limit is beating the floor by 244% and every other zone is
below average. Peer index says High Limit is doing slightly better than
comparable machines, North is genuinely strong, and Bar Tops is genuinely soft.

**The second table is actionable. The first is arithmetic dressed as insight.**

SlotSight returns both — but only so the UI can show you the trap. Nothing ranks
on floor index.

> **Watch for a cohort that is coextensive with a zone.** If a denomination
> exists only inside one zone, that zone's peer group is itself, its index is
> 1.000 by construction, and it can never be evaluated. This repo gives the High
> Limit salon a share of $1 units for exactly that reason — which is also how
> real high-limit rooms are laid out.

---

## Variance versus decline

Slot results are volatile in the short run. A machine can trail its peers for
three weeks on luck alone.

Act on that and you convert a fine machine, watch it revert to the mean, and
conclude your analytics tool does not work. **The second-order damage is worse
than the first.**

SlotSight confirms every finding against the immediately preceding window of
equal length and marks it `sustained`. Unsustained means *watch*, not *act*.

Here is what the planted decline in this dataset looks like:

| Window | Peer index |
|---|---:|
| Full 180 days | 0.90 |
| Trailing 30 days | **0.76** |

Invisible on a quarterly report. Unmistakable on a trend. That is the case worth
catching — a title that was always weak is trivial to find; one that decays out
from under you is not.

---

## When the data is lying

This dataset contains machine `NP-10307`. Over the last 30 days it reports a
realized hold of **23.4%** against a paytable par of **8.6%** — about **2.7× par**.

On a rank-by-win leaderboard, it is the best machine on the floor.

It is a broken meter. Sustained hold that far above par is a bill validator
fault, a meter rollover, or a miskeyed par. Real machines converge toward their
par; they do not triple it for three weeks.

**A rank-by-win report puts this machine first and invites someone to order
eight more of it.**

SlotSight evaluates data quality **first** and removes flagged machines from
performance rankings in **both** directions. An analytics tool that cannot say
*"I don't believe this number"* is not safe to act on.

---

## Deciding to convert

A conversion is a hypothesis, not a conclusion. Before recommending one:

1. Is the decline **sustained** across two windows?
2. Is it the **bank**, or one unit? One unit is a service call.
3. Are the **neighbours** weak too? Then it is the position, and swapping the
   title fixes nothing.
4. Is the target **compatible** — same denomination and game type? Otherwise it
   is a purchase, not a conversion.
5. Does the target beat the incumbent by enough to repay the **downtime**?
6. What is the **measurement plan**?

On the fifth point: SlotSight assumes only **half** the observed market edge
transfers to this floor. Different demographic, different position, different
competitive set. That coefficient is a judgement call, so it appears in every
impact estimate rather than being buried — and every conversion recommendation
carries a 30-day post-install measurement instruction, because measurement is
what replaces the assumption with a fact.

---

## Denomination economics

| Denom | Typical daily coin-in | Typical par hold |
|---|---:|---:|
| Penny | ~$2,450 | 8.3–11.8% |
| Nickel | ~$2,100 | 7.0–9.5% |
| Quarter | ~$3,150 | 6.0–8.2% |
| Dollar | ~$4,900 | 4.8–6.8% |
| $5 | ~$16,800 | 3.8–5.2% |

Higher denomination → **higher coin-in, lower hold**. Video poker is the extreme:
roughly 2.3× the coin-in of a reel game at about a third the hold, which is why
it needs its own cohort rather than being lumped in with reels.

---

## Where this lives in the code

| Concept | File |
|---|---|
| The formulas | [`analytics/metrics.py`](../apps/api/src/slotsight/analytics/metrics.py) |
| Peer indexing | [`analytics/floor.py`](../apps/api/src/slotsight/analytics/floor.py) |
| Variance vs decline, bad data | [`analytics/outliers.py`](../apps/api/src/slotsight/analytics/outliers.py) |
| The conversion checklist | [`analytics/recommend.py`](../apps/api/src/slotsight/analytics/recommend.py) |
| The four planted signals | [`seed/scenarios.py`](../apps/api/src/slotsight/seed/scenarios.py) |
