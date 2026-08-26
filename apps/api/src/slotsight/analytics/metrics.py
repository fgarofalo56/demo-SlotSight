"""Pure metric functions for slot floor analysis.

Deliberately dependency-free and side-effect-free: no database, no I/O, no
config. Every one of these is directly unit-testable, and the conversational
layer can never reach the data except through code that starts here.

Vocabulary, since it is not obvious outside the industry:

  **Coin-in**      Total amount wagered. NOT revenue. A single $20 bill
                   recycled through a machine thirty times is $600 of coin-in.
  **Theo win**     What the machine *should* win at its paytable: coin-in x par.
  **Actual win**   What it did win. Diverges from theo by short-run variance.
  **Hold %**       actual_win / coin_in. The realized take.
  **Par hold**     The hold the paytable is *designed* for. A property of the
                   game, not of its performance.
  **WPUPD**        Win Per Unit Per Day. The industry's headline metric.
  **Index**        A machine's WPUPD divided by a reference average. 1.00 is
                   exactly average; 0.80 is 20% below.

See docs/slot-analytics-primer.md for the longer version.
"""

from __future__ import annotations

from collections.abc import Sequence

CENTS_PER_DOLLAR = 100


def to_dollars(cents: int | float) -> float:
    """Convert integer cents to dollars, rounded to the cent.

    Money is stored and summed as integer cents precisely so that this
    conversion happens exactly once, at the presentation boundary.
    """
    return round(cents / CENTS_PER_DOLLAR, 2)


def wpupd(total_win_cents: int, days: int) -> float:
    """Win Per Unit Per Day, in dollars.

    The headline metric for slot performance. Normalizing by days is what
    makes a machine installed three weeks ago comparable to one installed
    three years ago.
    """
    if days <= 0:
        return 0.0
    return to_dollars(total_win_cents / days)


def coin_in_per_day(total_coin_in_cents: int, days: int) -> float:
    """Average daily coin-in, in dollars."""
    if days <= 0:
        return 0.0
    return to_dollars(total_coin_in_cents / days)


def hold_pct(actual_win_cents: int, coin_in_cents: int) -> float:
    """Realized hold as a fraction (0.0875 == 8.75%).

    Returns 0.0 for a machine with no coin-in rather than raising: a dark
    machine is a legitimate state, not an error, and callers aggregate across
    hundreds of machines where a few will always be dark.
    """
    if coin_in_cents <= 0:
        return 0.0
    return actual_win_cents / coin_in_cents


def index_to_average(value: float, average: float) -> float:
    """Ratio of a value to a reference average. 1.00 == exactly average.

    Returns 0.0 when the reference is non-positive, which happens only for an
    empty or fully-dark cohort.
    """
    if average <= 0:
        return 0.0
    return value / average


def hold_deviation_ratio(observed_hold: float, par_hold: float) -> float:
    """How far realized hold has drifted from the paytable's design.

    A ratio near 1.0 is healthy. Sustained values far above 1.0 are almost
    never a lucrative machine — they are a metering fault, a bill validator
    problem, or a miskeyed par. This is the guard that stops a naive
    rank-by-win engine from recommending you buy more broken machines.
    """
    if par_hold <= 0:
        return 0.0
    return observed_hold / par_hold


def linear_trend_slope(values: Sequence[float]) -> float:
    """Least-squares slope of a series against its index.

    Units are "value per step". Negative means declining. Implemented directly
    rather than pulled from numpy so this module stays dependency-free and
    trivially portable into a test or a notebook.
    """
    n = len(values)
    if n < 2:
        return 0.0

    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n

    numerator = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def pct_change(current: float, previous: float) -> float:
    """Percent change from previous to current. +12.5 means up 12.5%."""
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100.0


def peer_cohort_key(denomination_cents: int, game_type: str) -> str:
    """The cohort a machine should be benchmarked against.

    **This is the single most important judgement call in the whole module.**

    Comparing every machine to one floor-wide average is the obvious approach
    and it is wrong. A $5 High Limit machine earns several times what a penny
    bar-top earns; ranking them on the same scale simply sorts by
    denomination and tells you nothing you did not already know. Worse, it
    makes every penny machine look like a candidate for removal.

    Benchmarking within (denomination, game type) compares machines that are
    actually competing for the same guest and the same square footage. In this
    dataset the difference is stark: the High Limit zone reads as 3.5x on a
    floor-wide index but 1.14x against true peers. The first number is
    meaningless; the second is actionable.
    """
    return f"{denomination_cents}:{game_type}"


__all__ = [
    "CENTS_PER_DOLLAR",
    "coin_in_per_day",
    "hold_deviation_ratio",
    "hold_pct",
    "index_to_average",
    "linear_trend_slope",
    "pct_change",
    "peer_cohort_key",
    "to_dollars",
    "wpupd",
]
