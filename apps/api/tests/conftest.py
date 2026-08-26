"""Shared test fixtures.

DB-backed tests run against **SQLite in-memory** rather than Postgres so the
suite is hermetic and needs no service container. The seed and the analytics
are plain SQLAlchemy, so they behave identically - with one caveat worth
knowing: Postgres returns ``Decimal`` from ``SUM()`` over ``BIGINT`` while
SQLite returns ``int``. ``analytics.floor`` coerces at the SQL boundary, so
both work; a regression there would show up in the live stack but not here.
The ``docker compose`` smoke test in CI covers that gap.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from slotsight.models import Base
from slotsight.seed.generate import (
    build_competitors,
    build_machines,
    build_market,
    build_performance,
    build_zones,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def seeded_engine() -> AsyncGenerator:
    """One seeded in-memory database for the whole session.

    Session-scoped because generating 840 machines x 180 days is ~151k rows;
    doing that per-test would dominate the suite runtime.
    """
    from datetime import date

    import numpy as np
    from sqlalchemy import insert

    from slotsight.models import (
        CompetitorOffering,
        DailyPerformance,
        Machine,
        MarketTitle,
        Zone,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    rng = np.random.default_rng(20251107)
    today = date(2026, 8, 25)

    zones = build_zones()
    machines = build_machines(rng, 840, today)
    perf = build_performance(rng, machines, 180, today)
    market = build_market(rng, today)
    competitors = build_competitors(rng, today)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(insert(Zone), zones)
        await session.execute(insert(Machine), machines)
        for i in range(0, len(perf), 5_000):
            await session.execute(insert(DailyPerformance), perf[i : i + 5_000])
        await session.execute(insert(MarketTitle), market)
        await session.execute(insert(CompetitorOffering), competitors)
        await session.commit()

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(seeded_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(seeded_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def market(session: AsyncSession) -> AsyncGenerator:
    from slotsight.market.synthetic import SyntheticMarketProvider

    yield SyntheticMarketProvider(session)


@pytest.fixture(scope="session")
def analysis_end_date():
    """The last gaming day in the generated dataset.

    The generator lays down ``days`` rows ending the day before ``today``, so
    windows must anchor here rather than on the real current date - otherwise
    the suite starts failing the moment the machine clock rolls past the fixture.
    """
    from datetime import date, timedelta

    return date(2026, 8, 25) - timedelta(days=1)
