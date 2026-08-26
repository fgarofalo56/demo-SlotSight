"""SlotSight MCP server — exposes the live slot floor to any MCP client.

Point GitHub Copilot Chat at this and you can ask "which banks are fading?"
while you are writing code, and get an answer from the **real database** rather
than from the model's imagination.

## The architectural point

This server does not reimplement anything. It calls
``slotsight.agent.tools.dispatch`` — the exact same function the chat endpoint
uses, which in turn calls ``slotsight.analytics`` — the exact same code the REST
API uses.

    REST API  ─┐
    /api/chat ─┼─→ agent.tools.dispatch ─→ analytics/  ─→ PostgreSQL
    MCP server ┘

One implementation, three surfaces. That is deliberate: the fastest way to lose
trust in an analytics product is for the dashboard and the assistant to quote
different numbers for the same question, and the only reliable way to prevent it
is to make a second implementation impossible.

## Running it

Configured in ``.vscode/mcp.json``. Needs the database up:

    docker compose up -d db
    make seed

Standalone:

    uv run --project apps/api slotsight-mcp
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer

from slotsight.agent.tools import dispatch
from slotsight.db import dispose_engine, get_session_factory
from slotsight.market.synthetic import SyntheticMarketProvider

# stderr only: stdout is the MCP transport, and a stray print corrupts the
# protocol stream in a way that is genuinely unpleasant to debug.
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("slotsight-mcp")

# NOTE: MCP Python SDK 2.x renamed `FastMCP` to `MCPServer`. The decorator and
# run APIs are otherwise unchanged. `mcp>=2` is pinned in pyproject.toml - on
# 1.x this import fails with a clear migration message rather than anything
# subtle.
mcp = MCPServer(
    name="slotsight",
    instructions=(
        "Live slot floor analytics for Neon Palms Casino Resort (all data synthetic). "
        "Compare machines using peer_index, which benchmarks against the same "
        "denomination and game type. Do NOT use floor_index for ranking - it compares "
        "across all denominations and mostly just re-sorts by denomination. Machines "
        "flagged for data quality are excluded from performance lists; a hold far above "
        "paytable par is a metering fault, not a star performer."
    ),
)


async def _call(tool: str, args: dict[str, Any]) -> str:
    """Run one analytics tool and return its payload as JSON text."""
    factory = get_session_factory()
    try:
        async with factory() as session:
            result = await dispatch(tool, args, session, SyntheticMarketProvider(session))
            return json.dumps(result.payload, indent=2, default=str)
    except Exception as exc:
        logger.exception("Tool %s failed", tool)
        return json.dumps(
            {
                "error": f"{type(exc).__name__}: {exc}",
                "hint": (
                    "Is the database up and seeded? Try: docker compose up -d db && make seed"
                ),
            },
            indent=2,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
async def get_floor_summary(window_days: int = 30) -> str:
    """Headline KPIs for the whole floor plus a per-zone breakdown.

    Returns coin-in, win, WPUPD, hold %, and both peer and floor indices per
    zone. Use for broad questions: how is the floor doing, which zone is
    strongest.
    """
    return await _call("get_floor_summary", {"window_days": window_days})


@mcp.tool()
async def find_underperformers(
    window_days: int = 30,
    denomination_cents: int | None = None,
    game_type: str | None = None,
    zone: str | None = None,
    limit: int = 10,
) -> str:
    """Banks trailing their peer cohort, confirmed against a prior window.

    Short-run variance will not trigger a flag - a finding must be sustained.
    Machines with data-quality problems are already excluded. Results are
    grouped by bank because conversions are executed per bank, not per machine.

    Args:
        window_days: Trailing window in gaming days.
        denomination_cents: 1=penny, 5=nickel, 25=quarter, 100=$1, 500=$5.
        game_type: video_reel | mechanical_reel | video_poker | keno_multigame.
        zone: HL | MFN | MFS | PROM | BAR | NSM.
        limit: Maximum banks to return.
    """
    args: dict[str, Any] = {"window_days": window_days, "limit": limit}
    if denomination_cents is not None:
        args["denomination_cents"] = denomination_cents
    if game_type:
        args["game_type"] = game_type
    if zone:
        args["zone"] = zone
    return await _call("find_underperformers", args)


@mcp.tool()
async def get_recommendations(
    window_days: int = 30, action: str | None = None, limit: int = 10
) -> str:
    """Ranked, evidenced actions with rationale, impact estimates, and confidence.

    Args:
        window_days: Trailing window in gaming days.
        action: convert | remove | monitor | investigate | no_action.
        limit: Maximum recommendations to return.
    """
    args: dict[str, Any] = {"window_days": window_days, "limit": limit}
    if action:
        args["action"] = action
    return await _call("get_recommendations", args)


@mcp.tool()
async def compare_to_market(
    segment: str | None = None,
    exclude_owned: bool = False,
    rising_only: bool = False,
    limit: int = 10,
) -> str:
    """Title benchmarks from the market feed, flagged for whether we own them.

    NOTE: this market data is SYNTHETIC - generated for demonstration, not
    sourced from any real provider. Say so when citing it.

    Args:
        segment: e.g. 'Penny Video Reel'.
        exclude_owned: Only titles we do NOT currently operate (opportunities).
        rising_only: Only titles trending up.
        limit: Maximum titles to return.
    """
    args: dict[str, Any] = {
        "exclude_owned": exclude_owned,
        "rising_only": rising_only,
        "limit": limit,
    }
    if segment:
        args["segment"] = segment
    return await _call("compare_to_market", args)


@mcp.tool()
async def get_machine_detail(asset_number: str, window_days: int = 30) -> str:
    """Full detail for one machine, including a weekly trend and peer comparison.

    Args:
        asset_number: e.g. NP-21401.
        window_days: Trailing window in gaming days.
    """
    return await _call(
        "get_machine_detail", {"asset_number": asset_number, "window_days": window_days}
    )


@mcp.tool()
async def get_top_performers(window_days: int = 30, limit: int = 10) -> str:
    """Best machines against their peer cohort, with data-quality flags removed.

    The exclusion matters: the highest-"winning" machine on this floor is a
    metering fault, and a rank-by-win leaderboard would put it first.
    """
    return await _call("get_top_performers", {"window_days": window_days, "limit": limit})


@mcp.tool()
async def get_data_quality_flags(window_days: int = 30) -> str:
    """Machines whose realized hold is inconsistent with their paytable.

    Sustained hold far above par is characteristic of a metering or bill
    validator fault, not genuine performance. Check this before treating any
    unusually strong machine as real.
    """
    return await _call("get_data_quality_flags", {"window_days": window_days})


def main() -> int:
    """Console-script entry point. Speaks MCP over stdio."""
    logger.info("SlotSight MCP server starting (stdio)")
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        pass
    finally:
        # Best-effort pool cleanup. If the SDK already tore down the loop there
        # is nothing to dispose and nothing to report — the process is exiting.
        with contextlib.suppress(RuntimeError):
            asyncio.run(dispose_engine())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
