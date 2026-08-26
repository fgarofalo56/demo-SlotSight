"""Synthetic slot-floor generator.

Produces a complete, deterministic, believable casino floor: zones, machines,
180 days of daily meter readings, a synthetic market-intelligence feed, and
competitor observations.

    slotsight-seed --reset

**Deterministic by design.** The same seed always produces the same floor,
which is what lets the golden tests assert on specific conclusions and what
lets the stage demo tell the same story every time. Change
``SEED_RANDOM_SEED`` and the planted signals move — and
``tests/test_scenarios.py`` will fail, on purpose.

⚠  Every number here is invented. No real operator data was used. See NOTICE.md.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import delete, insert, select

from slotsight.config import get_settings
from slotsight.db import create_all, dispose_engine, drop_all, session_scope
from slotsight.models import (
    CompetitorOffering,
    DailyPerformance,
    Machine,
    MarketTitle,
    Zone,
)
from slotsight.seed import catalog as cat
from slotsight.seed import scenarios as sig

# Average bet per spin, in cents, by denomination. A penny slot is not a
# one-cent bet — it's 50-88 lines at a penny each.
AVG_BET_CENTS: dict[int, int] = {1: 75, 5: 150, 25: 250, 100: 320, 500: 1_000, 2500: 4_800}

PERF_CHUNK = 5_000


# ═══════════════════════════════════════════════════════════════════════════
# Zones
# ═══════════════════════════════════════════════════════════════════════════
def build_zones() -> list[dict[str, Any]]:
    return [
        {
            "id": i + 1,
            "code": z.code,
            "name": z.name,
            "description": z.description,
            "is_high_limit": z.is_high_limit,
        }
        for i, z in enumerate(cat.ZONES)
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Machines
# ═══════════════════════════════════════════════════════════════════════════
def _pick_denomination(rng: np.random.Generator, zone: cat.ZoneSpec) -> cat.DenomSpec:
    """High Limit draws from its own mix; everyone else from the main-floor mix."""
    by_cents = {d.cents: d for d in cat.DENOMINATIONS}
    if zone.is_high_limit:
        cents = list(cat.HIGH_LIMIT_DENOM_WEIGHTS)
        w = np.array([cat.HIGH_LIMIT_DENOM_WEIGHTS[c] for c in cents], dtype=float)
        return by_cents[cents[int(rng.choice(len(cents), p=w / w.sum()))]]
    pool = [d for d in cat.DENOMINATIONS if not d.high_limit_only]
    weights = np.array([d.weight for d in pool], dtype=float)
    return pool[int(rng.choice(len(pool), p=weights / weights.sum()))]


def _pick_title(rng: np.random.Generator, denom: cat.DenomSpec) -> cat.TitleSpec:
    """Bias game type by denomination the way a real floor is laid out.

    Reserved titles are excluded - they are placed explicitly by scenario code,
    not by random draw. See ``catalog.RESERVED_TITLES``.
    """
    available = [t for t in cat.TITLES if t.name not in cat.RESERVED_TITLES]
    if denom.cents >= 500:
        pool = [t for t in available if t.game_type in ("mechanical_reel", "video_reel")]
    elif denom.cents >= 100:
        pool = [t for t in available if t.game_type != "keno_multigame"]
    else:
        pool = available
    return pool[int(rng.integers(0, len(pool)))]


def build_machines(rng: np.random.Generator, total: int, today: date) -> list[dict[str, Any]]:
    """Lay out the floor as banks of homogeneous machines.

    Real floors are organized in banks — physically adjacent units of the same
    title and denomination — because that is how they are merchandised and how
    conversions are actually executed. Modeling banks rather than independent
    machines is what makes a bank-level recommendation meaningful.

    Asset numbering: ``NP-{zone}{bank:02d}{unit:02d}`` (e.g. ``NP-21401`` is
    zone 2, bank 14, unit 01).
    """
    machines: list[dict[str, Any]] = []

    for zone_idx, zone in enumerate(cat.ZONES):
        quota = round(total * zone.share)
        placed = 0
        bank_seq = 0

        while placed < quota:
            bank_seq += 1
            bank_id = f"NP-{zone_idx}{bank_seq:02d}"

            # ── SIGNAL 1: force the declining bank into existence ──────────
            is_declining = bank_id == sig.DECLINING_BANK_ID
            if is_declining:
                title = next(t for t in cat.TITLES if t.name == sig.DECLINING_BANK_TITLE)
                denom = next(
                    d for d in cat.DENOMINATIONS if d.cents == sig.DECLINING_BANK_DENOM_CENTS
                )
                size = sig.DECLINING_BANK_UNITS
            else:
                denom = _pick_denomination(rng, zone)
                title = _pick_title(rng, denom)
                max_size = 6 if zone.is_high_limit else 12
                size = int(rng.integers(4, max_size + 1))

            # ── SIGNAL 3: guarantee the anomaly machine's slot exists ──────
            anomaly_bank = sig.ANOMALY_ASSET_NUMBER[:-2]
            anomaly_unit = int(sig.ANOMALY_ASSET_NUMBER[-2:])
            if bank_id == anomaly_bank:
                size = max(size, anomaly_unit)

            size = min(size, quota - placed)
            if size <= 0:
                break

            cabinets = cat.CABINETS[title.manufacturer]
            cabinet = cabinets[int(rng.integers(0, len(cabinets)))]
            par = float(rng.uniform(denom.par_hold_min, denom.par_hold_max))
            par *= cat.GAME_TYPE_MODIFIERS[title.game_type][1]

            # Banks are installed as a unit, so units share an install date.
            age_days = int(rng.integers(45, 1_500))
            install = today - timedelta(days=age_days)

            for unit in range(1, size + 1):
                machines.append(
                    {
                        "asset_number": f"{bank_id}{unit:02d}",
                        "zone_id": zone_idx + 1,
                        "bank_id": bank_id,
                        "title": title.name,
                        "manufacturer": title.manufacturer,
                        "cabinet": cabinet,
                        "game_type": title.game_type,
                        "denomination_cents": denom.cents,
                        "par_hold_pct": round(par, 5),
                        "install_date": install,
                        "seats": 2 if "Dual" in cabinet else 1,
                        "status": "active",
                    }
                )
            placed += size

    return machines


# ═══════════════════════════════════════════════════════════════════════════
# Daily performance
# ═══════════════════════════════════════════════════════════════════════════
def build_performance(
    rng: np.random.Generator,
    machines: list[dict[str, Any]],
    days: int,
    today: date,
) -> list[dict[str, Any]]:
    """Generate one meter reading per machine per gaming day."""
    start = today - timedelta(days=days)
    denom_by_cents = {d.cents: d for d in cat.DENOMINATIONS}
    title_by_name = {t.name: t for t in cat.TITLES}
    zone_by_id = {i + 1: z for i, z in enumerate(cat.ZONES)}

    rows: list[dict[str, Any]] = []

    for m in machines:
        denom = denom_by_cents[m["denomination_cents"]]
        title = title_by_name[m["title"]]
        zone = zone_by_id[m["zone_id"]]
        coin_mult, _ = cat.GAME_TYPE_MODIFIERS[m["game_type"]]

        # Per-unit quality: even identical machines in a bank differ, because
        # position within the bank matters (aisle end vs. buried in the middle).
        #
        # sigma is deliberately modest. Crank it up and the peer-index
        # distribution widens until a fifth of the floor sits below the 0.85
        # underperformance threshold on noise alone - which buries the signals
        # this dataset exists to carry, and misrepresents how tightly a real
        # floor actually clusters.
        unit_quality = float(rng.lognormal(mean=0.0, sigma=0.085))

        base_usd = denom.base_coin_in_usd * coin_mult * title.popularity
        base_usd *= zone.traffic * unit_quality

        # SIGNAL 4: High Limit is running hot.
        if zone.code == sig.HEALTHY_ZONE_CODE:
            base_usd *= sig.HEALTHY_ZONE_BOOST

        is_declining = m["bank_id"] == sig.DECLINING_BANK_ID
        is_anomaly = m["asset_number"] == sig.ANOMALY_ASSET_NUMBER
        avg_bet = AVG_BET_CENTS[denom.cents]

        for offset in range(days):
            day = start + timedelta(days=offset)
            days_remaining = days - offset

            factor = cat.DAY_OF_WEEK_MULTIPLIER[day.weekday()]

            # Gentle decline with cabinet age — every machine fades a little.
            age = (day - m["install_date"]).days
            factor *= 1.0 - min(0.18, age / 9_000.0)

            # SIGNAL 1: linear decay across the trailing window.
            if is_declining and days_remaining <= sig.DECLINING_BANK_WINDOW_DAYS:
                progress = 1.0 - (days_remaining / sig.DECLINING_BANK_WINDOW_DAYS)
                factor *= 1.0 - (1.0 - sig.DECLINING_BANK_END_FACTOR) * progress

            # Day-to-day noise.
            factor *= float(rng.lognormal(mean=0.0, sigma=0.19))

            coin_in_cents = int(max(0.0, base_usd * factor) * 100)
            if coin_in_cents < 500:
                # Effectively dark for the day; still record the zero row so
                # downstream date ranges stay dense.
                rows.append(
                    {
                        "business_date": day,
                        "asset_number": m["asset_number"],
                        "coin_in_cents": 0,
                        "handle_pulls": 0,
                        "theo_win_cents": 0,
                        "actual_win_cents": 0,
                        "minutes_played": 0,
                    }
                )
                continue

            handle_pulls = max(1, coin_in_cents // avg_bet)
            theo_win = int(coin_in_cents * m["par_hold_pct"])

            # Short-run variance shrinks as handle grows — law of large numbers.
            sigma = float(np.clip(0.95 / np.sqrt(handle_pulls), 0.015, 0.55))
            actual_win = int(theo_win * (1.0 + rng.normal(0.0, sigma)))

            # SIGNAL 3: metering fault on the trailing window.
            if is_anomaly and days_remaining <= sig.ANOMALY_WINDOW_DAYS:
                actual_win = int(theo_win * sig.ANOMALY_HOLD_MULTIPLIER)

            # A machine can lose money on a day, but not unboundedly.
            actual_win = max(actual_win, -3 * theo_win)

            rows.append(
                {
                    "business_date": day,
                    "asset_number": m["asset_number"],
                    "coin_in_cents": coin_in_cents,
                    "handle_pulls": handle_pulls,
                    "theo_win_cents": theo_win,
                    "actual_win_cents": actual_win,
                    "minutes_played": int(min(1_440, handle_pulls * 0.11)),
                }
            )

    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Synthetic market intelligence  —  see NOTICE.md
# ═══════════════════════════════════════════════════════════════════════════
def _segment_for(denom_cents: int, game_type: str) -> str:
    denom_label = {
        1: "Penny",
        5: "Nickel",
        25: "Quarter",
        100: "Dollar",
        500: "High Limit",
        2500: "High Limit",
    }[denom_cents]
    type_label = {
        "video_reel": "Video Reel",
        "mechanical_reel": "Mechanical Reel",
        "video_poker": "Video Poker",
        "keno_multigame": "Multigame",
    }[game_type]
    return f"{denom_label} {type_label}"


def build_market(rng: np.random.Generator, today: date) -> list[dict[str, Any]]:
    """Benchmark rows for titles we own plus titles we don't.

    The titles we *don't* own are the point — a recommendation engine with no
    view of the wider market can only tell you what to remove, never what to
    put in its place.
    """
    as_of = today - timedelta(days=2)
    rows: list[dict[str, Any]] = []

    for title in cat.TITLES:
        provider = cat.MARKET_PROVIDERS[int(rng.integers(0, len(cat.MARKET_PROVIDERS)))]
        index = float(np.clip(rng.normal(title.popularity, 0.06), 0.55, 1.65))
        rows.append(
            {
                "provider": provider,
                "title": title.name,
                "manufacturer": title.manufacturer,
                "segment": _segment_for(1, title.game_type),
                "market_index": round(index, 3),
                "trend_30d_pct": round(float(rng.normal(0.0, 3.6)), 2),
                "install_base": int(rng.integers(400, 9_000)),
                "as_of_date": as_of,
            }
        )

    # ── SIGNAL 2: the hot title we do not own ──────────────────────────────
    for title in cat.MARKET_ONLY_TITLES:
        is_hot = title.name == sig.HOT_MARKET_TITLE
        rows.append(
            {
                "provider": cat.MARKET_PROVIDERS[0],
                "title": title.name,
                "manufacturer": title.manufacturer,
                "segment": (sig.HOT_MARKET_SEGMENT if is_hot else _segment_for(1, title.game_type)),
                "market_index": (
                    sig.HOT_MARKET_INDEX
                    if is_hot
                    else round(float(np.clip(rng.normal(title.popularity, 0.05), 0.6, 1.5)), 3)
                ),
                "trend_30d_pct": (
                    sig.HOT_MARKET_TREND_30D_PCT
                    if is_hot
                    else round(float(rng.normal(1.0, 2.5)), 2)
                ),
                "install_base": int(rng.integers(1_200, 7_500)),
                "as_of_date": as_of,
            }
        )

    return rows


def build_competitors(rng: np.random.Generator, today: date) -> list[dict[str, Any]]:
    observed = today - timedelta(days=5)
    pool = [t.name for t in cat.TITLES] + [t.name for t in cat.MARKET_ONLY_TITLES]
    rows: list[dict[str, Any]] = []

    for prop_name, market in cat.COMPETITOR_PROPERTIES:
        picks = rng.choice(len(pool), size=int(rng.integers(7, 12)), replace=False)
        for idx in picks:
            title = pool[int(idx)]
            # The hot title is well represented at competitors — that's the
            # signal a floor manager would actually notice walking a rival floor.
            base = 22 if title == sig.HOT_MARKET_TITLE else 8
            rows.append(
                {
                    "property_name": prop_name,
                    "market": market,
                    "title": title,
                    "unit_count": int(base + rng.integers(0, 14)),
                    "promo_note": cat.PROMO_NOTES[int(rng.integers(0, len(cat.PROMO_NOTES)))],
                    "observed_date": observed,
                }
            )

    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Orchestration
# ═══════════════════════════════════════════════════════════════════════════
async def seed(*, reset: bool = False, quiet: bool = False) -> dict[str, int]:
    settings = get_settings()
    rng = np.random.default_rng(settings.seed_random_seed)
    today = date.today()

    def say(msg: str) -> None:
        if not quiet:
            print(msg, flush=True)

    if reset:
        say("  dropping existing tables ...")
        await drop_all()

    await create_all()

    async with session_scope() as session:
        existing = (await session.execute(select(Machine.asset_number).limit(1))).first()
        if existing and not reset:
            say("  database already seeded - use --reset to regenerate")
            count = len((await session.execute(select(Machine.asset_number))).all())
            return {"machines": count, "skipped": 1}

        if reset:
            for model in (CompetitorOffering, MarketTitle, DailyPerformance, Machine, Zone):
                await session.execute(delete(model))

        zones = build_zones()
        await session.execute(insert(Zone), zones)
        say(f"  zones                {len(zones):>8,}")

        machines = build_machines(rng, settings.seed_machine_count, today)
        await session.execute(insert(Machine), machines)
        say(f"  machines             {len(machines):>8,}")

        perf = build_performance(rng, machines, settings.seed_days_of_history, today)
        for i in range(0, len(perf), PERF_CHUNK):
            await session.execute(insert(DailyPerformance), perf[i : i + PERF_CHUNK])
        say(f"  daily performance    {len(perf):>8,}")

        market = build_market(rng, today)
        await session.execute(insert(MarketTitle), market)
        say(f"  market benchmarks    {len(market):>8,}")

        competitors = build_competitors(rng, today)
        await session.execute(insert(CompetitorOffering), competitors)
        say(f"  competitor sightings {len(competitors):>8,}")

    return {
        "zones": len(zones),
        "machines": len(machines),
        "performance": len(perf),
        "market": len(market),
        "competitors": len(competitors),
    }


async def _amain(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="slotsight-seed",
        description="Generate the synthetic Neon Palms slot floor.",
    )
    ap.add_argument("--reset", action="store_true", help="drop and regenerate everything")
    ap.add_argument("--quiet", action="store_true", help="suppress progress output")
    args = ap.parse_args(argv)

    settings = get_settings()
    if not args.quiet:
        print(f"\n  Seeding {settings.property_name}")
        print(
            f"  seed={settings.seed_random_seed}  machines={settings.seed_machine_count}"
            f"  days={settings.seed_days_of_history}\n"
        )

    try:
        await seed(reset=args.reset, quiet=args.quiet)
    except Exception as exc:
        print(f"\n  seed failed: {exc}\n", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()

    if not args.quiet:
        print("\n  done. All data is synthetic - see NOTICE.md\n")
    return 0


def main() -> int:
    """Console-script entry point."""
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
