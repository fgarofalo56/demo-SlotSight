"""Deterministic slot floor analytics.

**This package contains no AI and no network calls.** Every conclusion
SlotSight reaches is produced here, by ordinary code, against ordinary SQL,
covered by ordinary tests.

The conversational layer in ``slotsight.agent`` is a presentation shell over
this package. It may only reach data through these functions - it never writes
its own query. The consequence is the property that makes the whole system
trustworthy: **every number the assistant says is a number a test already
covers, and the model cannot invent a figure even if it tries.**

Read in this order:

    metrics.py     pure functions - WPUPD, hold, peer indexing
    floor.py       the one aggregation query everything else builds on
    outliers.py    underperformers, top performers, untrustworthy data
    recommend.py   the payoff - actions with evidence attached
"""

from slotsight.analytics import floor, metrics, outliers, recommend

__all__ = ["floor", "metrics", "outliers", "recommend"]
