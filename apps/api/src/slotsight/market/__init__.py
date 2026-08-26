"""Market intelligence — the pluggable seam.

In a real deployment this is where a commercial slot-performance data
subscription would plug in. **This repository ships exactly one implementation
and it is synthetic.** There is no scraping, no vendor API, no data licence,
and no affiliation with any real provider. See NOTICE.md.

The seam exists for two reasons:

1. **Honesty.** Making the boundary explicit is more useful to someone reading
   this repo than pretending a real feed exists. You can see precisely what an
   adapter has to supply.
2. **Testability.** The recommendation engine depends on the ``Protocol``, not
   on the synthetic class, so tests inject fixed benchmarks and assert on
   conclusions without touching a database.

To add a real provider: implement ``MarketIntelProvider`` and swap it in
``routers/deps.py``. Nothing above this line changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TitleBenchmark:
    """How a game title performs in comparable markets."""

    title: str
    manufacturer: str
    segment: str
    provider: str
    market_index: float
    trend_30d_pct: float
    install_base: int
    as_of_date: date

    @property
    def is_rising(self) -> bool:
        return self.trend_30d_pct > 2.0

    @property
    def outperformance_pct(self) -> float:
        """How far above (or below) comparable-market average, in percent."""
        return (self.market_index - 1.0) * 100.0


@dataclass(frozen=True)
class CompetitorSighting:
    """A title observed on a competitor's floor."""

    property_name: str
    market: str
    title: str
    unit_count: int
    promo_note: str
    observed_date: date


@runtime_checkable
class MarketIntelProvider(Protocol):
    """What any market-intelligence source must supply."""

    @property
    def name(self) -> str:
        """Human-readable provider name, shown in the UI for attribution."""
        ...

    @property
    def is_synthetic(self) -> bool:
        """True when this data is generated rather than sourced.

        Surfaced all the way to the UI. A recommendation grounded in invented
        benchmarks must never be presented as though it came from real market
        data.
        """
        ...

    async def title_benchmarks(self, segment: str | None = None) -> list[TitleBenchmark]: ...

    async def competitor_offerings(self, title: str | None = None) -> list[CompetitorSighting]: ...


__all__ = [
    "CompetitorSighting",
    "MarketIntelProvider",
    "TitleBenchmark",
]
