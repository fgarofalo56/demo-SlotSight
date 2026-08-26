"""Health and readiness."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight import __version__
from slotsight.config import Settings, get_settings
from slotsight.db import get_session
from slotsight.models import Machine
from slotsight.schemas import DependencyStatus, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Report service and dependency health.

    Deliberately reports *whether* Azure OpenAI is configured, never the
    endpoint or any token. Verifying a credential should confirm presence and
    behaviour, never reveal a value. See SECURITY.md.
    """
    deps: list[DependencyStatus] = []
    overall = "ok"

    # ── Database ───────────────────────────────────────────────────────────
    try:
        count = (await session.execute(select(Machine.asset_number).limit(1))).first()
        if count is None:
            deps.append(
                DependencyStatus(
                    name="database",
                    status="degraded",
                    detail="Connected, but no machines found. Run: make seed",
                )
            )
            overall = "degraded"
        else:
            deps.append(
                DependencyStatus(name="database", status="ok", detail="Connected and seeded.")
            )
    except Exception as exc:
        deps.append(
            DependencyStatus(
                name="database",
                status="unavailable",
                detail=f"{type(exc).__name__}: connection failed.",
            )
        )
        overall = "degraded"

    # ── Azure OpenAI ───────────────────────────────────────────────────────
    #
    # Reports CONFIGURATION, not reachability, and says so. Claiming "ok" here
    # on the strength of two environment variables would be a green light over
    # a path that can still fail on auth - which is the failure mode this whole
    # endpoint exists to avoid. Actually proving the credential works means
    # minting a token on every health check, which is both slow and rude to the
    # token service.
    if settings.azure_openai_configured:
        deps.append(
            DependencyStatus(
                name="azure_openai",
                status="configured",
                detail=(
                    f"Endpoint and deployment '{settings.azure_openai_deployment}' are set; "
                    f"auth is Entra ID. NOT verified - configuration alone does not prove "
                    f"the credential resolves. POST /api/chat is the real check."
                ),
            )
        )
    else:
        deps.append(
            DependencyStatus(
                name="azure_openai",
                status="not_configured",
                detail=(
                    "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT are not set. "
                    "Analytics endpoints work normally; POST /api/chat will return 503. "
                    "See docs/troubleshooting.md."
                ),
            )
        )

    return HealthResponse(
        status=overall,
        version=__version__,
        property_name=settings.property_name,
        dependencies=deps,
    )
