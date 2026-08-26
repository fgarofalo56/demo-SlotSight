"""SQLAlchemy ORM models for the SlotSight slot floor.

Two conventions worth calling out, because they're the kind of thing a
code-generating agent gets wrong by default:

1. **Money is stored as integer cents**, never float. Floating point money
   accumulates error across a 180-day × 840-machine aggregation, and slot
   analytics is exactly the domain where a rounding drift becomes a wrong
   business recommendation. Ratios and percentages *are* floats — they're
   derived, not summed.

2. **There is no player table, and there never will be.** SlotSight models
   machines and money, never people. See NOTICE.md.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for every SlotSight table."""


# ═══════════════════════════════════════════════════════════════════════════
# Floor geography
# ═══════════════════════════════════════════════════════════════════════════
class Zone(Base):
    """A named area of the gaming floor.

    Zones matter because floor-average comparisons are misleading across
    them — a High Limit machine and a penny bar-top are not peers.
    """

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(256), default="")
    is_high_limit: Mapped[bool] = mapped_column(Boolean, default=False)

    machines: Mapped[list[Machine]] = relationship(back_populates="zone")

    def __repr__(self) -> str:
        return f"<Zone {self.code} {self.name!r}>"


# ═══════════════════════════════════════════════════════════════════════════
# Assets
# ═══════════════════════════════════════════════════════════════════════════
class Machine(Base):
    """A single slot machine on the floor, keyed by its asset number.

    ``asset_number`` is a natural key (e.g. ``NP-21401``) because that's what
    slot techs and floor managers actually say out loud. Surrogate integer keys
    would force a translation layer at every human touchpoint.

    Format is ``NP-{zone}{bank:02d}{unit:02d}`` — so ``NP-21401`` is zone 2,
    bank 14, unit 01.
    """

    __tablename__ = "machines"

    asset_number: Mapped[str] = mapped_column(String(16), primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)

    # A "bank" is a physically adjacent group, usually the same title.
    # Conversions happen at bank granularity, not per-machine.
    bank_id: Mapped[str] = mapped_column(String(16), index=True)

    title: Mapped[str] = mapped_column(String(80), index=True)
    manufacturer: Mapped[str] = mapped_column(String(48), index=True)
    cabinet: Mapped[str] = mapped_column(String(48))
    game_type: Mapped[str] = mapped_column(String(32), index=True)

    # Denomination in cents: 1 = penny, 5 = nickel, 25 = quarter, 100 = dollar.
    denomination_cents: Mapped[int] = mapped_column(Integer, index=True)

    # Theoretical hold — the share of coin-in the game is *designed* to keep.
    # 0.0875 == 8.75%. Set by the paytable, not by performance.
    par_hold_pct: Mapped[float] = mapped_column(Float)

    install_date: Mapped[date] = mapped_column(Date)
    seats: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)

    zone: Mapped[Zone] = relationship(back_populates="machines")
    performance: Mapped[list[DailyPerformance]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Machine {self.asset_number} {self.title!r}>"


# ═══════════════════════════════════════════════════════════════════════════
# Performance
# ═══════════════════════════════════════════════════════════════════════════
class DailyPerformance(Base):
    """One machine's metered numbers for one gaming day.

    This is the fact table — everything SlotSight concludes traces back here.
    """

    __tablename__ = "daily_performance"
    __table_args__ = (
        UniqueConstraint("business_date", "asset_number", name="uq_perf_date_asset"),
        # The dominant query shape is "this machine over a window", so the
        # composite index leads with asset_number.
        Index("ix_perf_asset_date", "asset_number", "business_date"),
        Index("ix_perf_date", "business_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_date: Mapped[date] = mapped_column(Date)
    asset_number: Mapped[str] = mapped_column(
        ForeignKey("machines.asset_number", ondelete="CASCADE")
    )

    # Total amount wagered. This is NOT revenue — a single dollar recycled
    # through the machine twenty times counts as twenty dollars of coin-in.
    coin_in_cents: Mapped[int] = mapped_column(BigInteger)

    handle_pulls: Mapped[int] = mapped_column(Integer)

    # What the game *should* have won at par: coin_in × par_hold_pct.
    theo_win_cents: Mapped[int] = mapped_column(BigInteger)

    # What it actually won. Diverges from theo by short-run variance — which
    # is exactly why a single bad week is not evidence of a bad machine.
    actual_win_cents: Mapped[int] = mapped_column(BigInteger)

    minutes_played: Mapped[int] = mapped_column(Integer, default=0)

    machine: Mapped[Machine] = relationship(back_populates="performance")

    def __repr__(self) -> str:
        return f"<Perf {self.asset_number} {self.business_date} win={self.actual_win_cents}>"


# ═══════════════════════════════════════════════════════════════════════════
# External market intelligence  —  SYNTHETIC. See NOTICE.md.
# ═══════════════════════════════════════════════════════════════════════════
class MarketTitle(Base):
    """A benchmark record for a game title in comparable markets.

    In a real deployment this is bought from a commercial provider. Here it is
    entirely generated. ``provider`` holds a fictional placeholder name showing
    *where* a real adapter would plug in — see ``slotsight.market``.
    """

    __tablename__ = "market_titles"
    __table_args__ = (UniqueConstraint("provider", "title", "as_of_date", name="uq_market_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(48), index=True)
    title: Mapped[str] = mapped_column(String(80), index=True)
    manufacturer: Mapped[str] = mapped_column(String(48))
    segment: Mapped[str] = mapped_column(String(48), index=True)

    # 1.00 == exactly the comparable-market average for this segment.
    market_index: Mapped[float] = mapped_column(Float)
    trend_30d_pct: Mapped[float] = mapped_column(Float)
    install_base: Mapped[int] = mapped_column(Integer, default=0)
    as_of_date: Mapped[date] = mapped_column(Date, index=True)

    def __repr__(self) -> str:
        return f"<MarketTitle {self.title!r} idx={self.market_index:.2f}>"


class CompetitorOffering(Base):
    """What nearby (fictional) properties are running. SYNTHETIC."""

    __tablename__ = "competitor_offerings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_name: Mapped[str] = mapped_column(String(80), index=True)
    market: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(80), index=True)
    unit_count: Mapped[int] = mapped_column(Integer)
    promo_note: Mapped[str] = mapped_column(String(256), default="")
    observed_date: Mapped[date] = mapped_column(Date, index=True)

    def __repr__(self) -> str:
        return f"<Competitor {self.property_name!r} {self.title!r} x{self.unit_count}>"


__all__ = [
    "Base",
    "CompetitorOffering",
    "DailyPerformance",
    "Machine",
    "MarketTitle",
    "Zone",
]
