"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slotsight import __version__
from slotsight.agent.azure_openai import close_client
from slotsight.config import get_settings
from slotsight.db import create_all, dispose_engine
from slotsight.routers import chat, floor, health, machines, market, recommendations

DESCRIPTION = """\
**SlotSight** — intelligent slot floor performance assistant for the fictional
**Neon Palms Casino Resort**.

A teaching reference implementation for spec-driven development with GitHub
Copilot. Every number is synthetic; see `NOTICE.md`.

### Architecture

The analytics are **deterministic SQL**. The AI only phrases the answer.

`/api/chat` is a tool-calling shell that may reach data *only* through the same
functions the REST endpoints use — so every figure the assistant quotes is one
a test already covers. `/api/chat` is also the only endpoint that requires
Azure OpenAI; everything else runs with no cloud dependency.

### Two metrics worth understanding before reading any number

- **`peer_index`** — a machine against the same denomination and game type.
  This is the actionable one.
- **`floor_index`** — a machine against the entire floor. Included only to
  demonstrate how badly it misleads: it mostly just sorts by denomination.
"""


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = logging.getLogger("slotsight")

    log.info("Starting SlotSight %s for %s", __version__, settings.property_name)
    if not settings.azure_openai_configured:
        log.warning(
            "Azure OpenAI not configured - POST /api/chat will return 503. "
            "Analytics endpoints are unaffected. See docs/troubleshooting.md."
        )

    try:
        await create_all()
    except Exception as exc:
        log.error("Could not prepare database schema: %s", exc)

    # Opt-in, and only when the floor is genuinely empty. This is what makes
    # `azd up` produce a working demo instead of a correctly-deployed empty one.
    # See Settings.seed_on_startup.
    if settings.seed_on_startup:
        try:
            from sqlalchemy import func, select

            from slotsight.db import session_scope
            from slotsight.models import Machine
            from slotsight.seed.generate import seed as run_seed

            async with session_scope() as session:
                count = (
                    await session.execute(select(func.count()).select_from(Machine))
                ).scalar_one()

            if count:
                log.info("Floor already seeded (%d machines) - skipping startup seed", count)
            else:
                log.info("Empty floor detected; generating synthetic data ...")
                result = await run_seed(reset=False, quiet=True)
                log.info("Startup seed complete: %s", result)
        except Exception as exc:
            # Never block startup on the seed. /api/health will report the
            # database as degraded, which is the honest signal.
            log.error("Startup seed failed: %s", exc)

    yield

    await close_client()
    await dispose_engine()
    log.info("SlotSight stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SlotSight API",
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    for router in (
        health.router,
        floor.router,
        machines.router,
        recommendations.router,
        market.router,
        chat.router,
    ):
        app.include_router(router, prefix="/api")

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "SlotSight API",
            "version": __version__,
            "property": settings.property_name,
            "docs": "/docs",
            "health": "/api/health",
            "notice": "All data is synthetic. See NOTICE.md.",
        }

    return app


app = create_app()
