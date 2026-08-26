"""Conversational endpoint.

The only endpoint in SlotSight that requires Azure OpenAI. Everything else is
deterministic SQL and works with no cloud dependency at all — a deliberate
split, so a missing credential degrades one feature instead of the product.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.agent.azure_openai import AzureOpenAINotConfiguredError
from slotsight.agent.orchestrator import run_conversation
from slotsight.config import Settings, get_settings
from slotsight.db import get_session
from slotsight.market import MarketIntelProvider
from slotsight.routers.common import get_market_provider
from slotsight.schemas import ChatRequest, ChatResponse, ToolCallRecord

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="Ask a question in plain English")
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    market: MarketIntelProvider = Depends(get_market_provider),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Answer a natural-language question about the floor.

    The response includes ``tool_calls`` — the exact analytics functions that
    ran, with their arguments. That makes every answer auditable: you can
    re-run the same functions through the REST API and get the same numbers.

    **Requires Azure OpenAI.** Returns 503 with remediation steps when it is
    not configured. The analytics endpoints are unaffected.
    """
    try:
        result = await run_conversation(
            message=request.message,
            session=session,
            market=market,
            settings=settings,
            window_days=request.window_days,
        )
    except AzureOpenAINotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "azure_openai_not_configured",
                "message": str(exc),
                "missing": exc.missing,
                "unaffected_endpoints": [
                    "/api/floor/summary",
                    "/api/machines",
                    "/api/recommendations",
                    "/api/outliers",
                    "/api/market/titles",
                ],
                "docs": "docs/troubleshooting.md",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_failure",
                "message": (
                    f"The Azure OpenAI call failed: {type(exc).__name__}. Check that "
                    f"`az login` is current and that your identity holds the "
                    f"'Cognitive Services OpenAI User' role on the resource. "
                    f"See docs/troubleshooting.md."
                ),
            },
        ) from exc

    return ChatResponse(
        answer=result.answer,
        tool_calls=[
            ToolCallRecord(tool=c.tool, arguments=c.arguments, result_summary=c.result_summary)
            for c in result.tool_calls
        ],
        window_days=request.window_days,
        model_deployment=settings.azure_openai_deployment or "",
        grounded=result.grounded,
    )
