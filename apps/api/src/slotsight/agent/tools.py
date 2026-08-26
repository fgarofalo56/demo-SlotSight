"""Tool definitions and dispatch for the conversational layer.

**The model never writes SQL.** It selects from this fixed set of functions,
each of which delegates to ``slotsight.analytics`` — the same deterministic
code the REST API uses. The consequence is the property that makes the
assistant trustworthy: every figure it quotes is one a test already covers,
and it cannot invent a number even when it wants to.

Two constraints shape every tool here:

**Payloads are aggressively truncated.** 840 machines of detail would blow the
context window and degrade answer quality. Tools return the few rows that
matter plus the counts needed to describe the rest honestly.

**Every payload carries its provenance.** Row counts, window bounds, and the
synthetic-data flag travel with the numbers, so the model can attribute
accurately instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import (
    floor_summary,
    machine_daily_series,
    machine_metrics,
)
from slotsight.analytics.outliers import (
    detect_data_quality,
    find_top_performers,
    find_underperformers,
)
from slotsight.analytics.recommend import build_recommendations
from slotsight.market import MarketIntelProvider
from slotsight.models import Machine

MAX_ROWS = 12


@dataclass(frozen=True)
class ToolResult:
    payload: dict[str, Any]
    summary: str


# ═══════════════════════════════════════════════════════════════════════════
# Schemas exposed to the model
# ═══════════════════════════════════════════════════════════════════════════
_WINDOW = {
    "type": "integer",
    "description": "Trailing window in gaming days. Default 30. 'this month' == 30.",
    "minimum": 1,
    "maximum": 365,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_floor_summary",
            "description": (
                "Headline KPIs for the whole floor plus a per-zone breakdown: coin-in, "
                "win, WPUPD, hold %, and both peer and floor indices per zone. Use this "
                "for broad questions like 'how is the floor doing' or 'which zone is "
                "strongest'."
            ),
            "parameters": {
                "type": "object",
                "properties": {"window_days": _WINDOW},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_underperformers",
            "description": (
                "Machines trailing their peer cohort, confirmed against a prior window "
                "so short-run variance does not trigger a false flag. Machines with "
                "data-quality problems are already excluded. Use for 'what is "
                "underperforming', 'which machines should we convert', 'what is losing "
                "money'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": _WINDOW,
                    "denomination_cents": {
                        "type": "integer",
                        "description": (
                            "Filter by denomination. 1=penny, 5=nickel, 25=quarter, "
                            "100=$1, 500=$5, 2500=$25."
                        ),
                    },
                    "game_type": {
                        "type": "string",
                        "enum": [
                            "video_reel",
                            "mechanical_reel",
                            "video_poker",
                            "keno_multigame",
                        ],
                    },
                    "zone": {
                        "type": "string",
                        "description": (
                            "Zone code: HL (High Limit), MFN (Main Floor North), MFS "
                            "(Main Floor South), PROM (Promenade), BAR (Bar Tops), "
                            "NSM (Non-Smoking)."
                        ),
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": (
                "Ranked, evidenced actions: conversions, removals, monitoring, metering "
                "investigations, and explicit all-clears. Each carries rationale, "
                "evidence, estimated annual impact, and confidence. Use for 'what should "
                "we do', 'what do you recommend', 'where is the biggest opportunity'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": _WINDOW,
                    "action": {
                        "type": "string",
                        "enum": [
                            "convert",
                            "remove",
                            "monitor",
                            "investigate",
                            "no_action",
                        ],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_to_market",
            "description": (
                "Title benchmarks from the market intelligence feed, with a flag for "
                "whether we already operate each title. Use for 'what is hot right now', "
                "'what should we convert TO', 'what are competitors running'. NOTE: this "
                "data is SYNTHETIC - always say so when citing it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "segment": {
                        "type": "string",
                        "description": "e.g. 'Penny Video Reel'.",
                    },
                    "exclude_owned": {
                        "type": "boolean",
                        "description": "Only titles we do NOT currently operate.",
                    },
                    "rising_only": {"type": "boolean"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_machine_detail",
            "description": (
                "Full detail for one machine by asset number, including a weekly trend "
                "and its peer comparison. Use when the user names a specific machine "
                "such as NP-21401."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_number": {"type": "string"},
                    "window_days": _WINDOW,
                },
                "required": ["asset_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_performers",
            "description": (
                "Best machines against their peer cohort, with data-quality flags "
                "removed. Use for 'what is working', 'best machines', 'what should we "
                "buy more of'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": _WINDOW,
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality_flags",
            "description": (
                "Machines whose realized hold is inconsistent with their paytable - "
                "usually a metering or bill-validator fault rather than real "
                "performance. Use for 'is the data reliable', 'anything look wrong', or "
                "whenever a machine's numbers look implausibly good."
            ),
            "parameters": {
                "type": "object",
                "properties": {"window_days": _WINDOW},
                "required": [],
            },
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# Rendering helpers - compact, model-friendly shapes
# ═══════════════════════════════════════════════════════════════════════════
def _machine_row(m: Any) -> dict[str, Any]:
    return {
        "asset_number": m.asset_number,
        "bank_id": m.bank_id,
        "title": m.title,
        "zone": m.zone_code,
        "denomination_cents": m.denomination_cents,
        "game_type": m.game_type,
        "wpupd_dollars": m.wpupd,
        "peer_index": m.peer_index,
        "peer_cohort_size": m.peer_cohort_size,
        "hold_pct": round(m.hold_pct * 100, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Dispatch
# ═══════════════════════════════════════════════════════════════════════════
async def dispatch(
    name: str,
    args: dict[str, Any],
    session: AsyncSession,
    market: MarketIntelProvider,
    default_window: int = 30,
) -> ToolResult:
    """Execute one tool call. Raises ValueError for an unknown tool."""
    days = int(args.get("window_days") or default_window)
    limit = min(int(args.get("limit") or MAX_ROWS), MAX_ROWS)

    # ── Floor summary ──────────────────────────────────────────────────────
    if name == "get_floor_summary":
        s = await floor_summary(session, days=days)
        payload = {
            "window_days": s.window_days,
            "date_range": f"{s.start_date} to {s.end_date}",
            "machine_count": s.machine_count,
            "coin_in_dollars": round(s.total_coin_in_cents / 100, 2),
            "win_dollars": round(s.total_actual_win_cents / 100, 2),
            "floor_wpupd_dollars": s.floor_wpupd,
            "floor_hold_pct": round(s.floor_hold_pct * 100, 2),
            "wpupd_change_vs_prior_window_pct": s.wpupd_change_pct,
            "zones": [
                {
                    "zone": z.zone_code,
                    "name": z.zone_name,
                    "machines": z.machine_count,
                    "wpupd_dollars": z.wpupd,
                    "peer_index": z.peer_index,
                    "floor_index": z.floor_index,
                }
                for z in s.zones
            ],
            "_note": (
                "peer_index compares like with like and is the actionable number. "
                "floor_index compares across all denominations and is included only "
                "to show how misleading it is."
            ),
        }
        return ToolResult(
            payload,
            f"Floor summary over {days}d: {s.machine_count} machines, "
            f"WPUPD ${s.floor_wpupd:,.2f} ({s.wpupd_change_pct:+.1f}%).",
        )

    # ── Underperformers ────────────────────────────────────────────────────
    if name == "find_underperformers":
        unders = await find_underperformers(session, days=days)

        if (denom := args.get("denomination_cents")) is not None:
            unders = [u for u in unders if u.machine.denomination_cents == int(denom)]
        if gt := args.get("game_type"):
            unders = [u for u in unders if u.machine.game_type == gt]
        if zone := args.get("zone"):
            unders = [u for u in unders if u.machine.zone_code.upper() == zone.upper()]

        total = len(unders)

        # Roll up to banks so the model talks about actionable units, not 187
        # individual machines.
        banks: dict[str, list[Any]] = {}
        for u in unders:
            banks.setdefault(u.machine.bank_id, []).append(u)

        bank_rows = sorted(
            (
                {
                    "bank_id": bid,
                    "title": items[0].machine.title,
                    "zone": items[0].machine.zone_code,
                    "denomination_cents": items[0].machine.denomination_cents,
                    "game_type": items[0].machine.game_type,
                    "flagged_units": len(items),
                    "avg_peer_index": round(sum(i.peer_index for i in items) / len(items), 3),
                    "avg_prior_peer_index": round(
                        sum(i.prior_peer_index for i in items) / len(items), 3
                    ),
                    "avg_wpupd_dollars": round(sum(i.machine.wpupd for i in items) / len(items), 2),
                    "severity": items[0].severity,
                    "asset_numbers": [i.machine.asset_number for i in items][:8],
                }
                for bid, items in banks.items()
            ),
            key=lambda b: b["avg_peer_index"],
        )[:limit]

        payload = {
            "window_days": days,
            "total_machines_flagged": total,
            "total_banks_flagged": len(banks),
            "banks_returned": len(bank_rows),
            "banks": bank_rows,
            "_note": (
                "Grouped by bank because conversions are executed per bank, not per "
                "machine. peer_index below 1.00 means below the average of comparable "
                "units. Machines with data-quality flags are already excluded."
            ),
        }
        return ToolResult(
            payload,
            f"{total} machines across {len(banks)} banks below peer average over {days}d.",
        )

    # ── Recommendations ────────────────────────────────────────────────────
    if name == "get_recommendations":
        recs = await build_recommendations(session, market, days=days)
        if action := args.get("action"):
            recs = [r for r in recs if r.action == action]

        rows = [
            {
                "id": r.id,
                "action": r.action,
                "priority": r.priority,
                "subject": r.subject_id,
                "headline": r.headline,
                "rationale": r.rationale,
                "evidence": r.evidence,
                "suggested_title": r.suggested_title,
                "estimated_annual_impact_dollars": r.estimated_annual_impact_dollars,
                "confidence": r.confidence,
                "uses_synthetic_market_data": r.uses_synthetic_market_data,
                "monitoring_instruction": r.monitoring_instruction,
            }
            for r in recs[:limit]
        ]
        return ToolResult(
            {
                "window_days": days,
                "total": len(recs),
                "returned": len(rows),
                "recommendations": rows,
            },
            f"{len(recs)} recommendations over {days}d; returned top {len(rows)}.",
        )

    # ── Market ─────────────────────────────────────────────────────────────
    if name == "compare_to_market":
        benchmarks = await market.title_benchmarks(segment=args.get("segment"))
        owned = {t for (t,) in (await session.execute(select(Machine.title).distinct())).all()}
        if args.get("rising_only"):
            benchmarks = [b for b in benchmarks if b.is_rising]
        if args.get("exclude_owned"):
            benchmarks = [b for b in benchmarks if b.title not in owned]

        rows = [
            {
                "title": b.title,
                "manufacturer": b.manufacturer,
                "segment": b.segment,
                "market_index": b.market_index,
                "outperformance_pct": round(b.outperformance_pct, 1),
                "trend_30d_pct": b.trend_30d_pct,
                "on_our_floor": b.title in owned,
                "provider": b.provider,
            }
            for b in benchmarks[:limit]
        ]
        return ToolResult(
            {
                "is_synthetic": market.is_synthetic,
                "provider": market.name,
                "disclaimer": (
                    "SYNTHETIC market data. Generated for demonstration; not sourced "
                    "from any real provider. State this when citing these figures."
                ),
                "total": len(benchmarks),
                "titles": rows,
            },
            f"{len(rows)} market titles returned (synthetic feed).",
        )

    # ── Machine detail ─────────────────────────────────────────────────────
    if name == "get_machine_detail":
        asset = str(args.get("asset_number", "")).strip().upper()
        machines = await machine_metrics(session, days=days)
        target = next((m for m in machines if m.asset_number.upper() == asset), None)
        if target is None:
            return ToolResult(
                {"error": f"No machine '{asset}' with data in the last {days} days."},
                f"Machine {asset} not found.",
            )

        cohort = [m for m in machines if m.peer_cohort == target.peer_cohort]
        peer_avg = round(sum(m.wpupd for m in cohort) / len(cohort), 2) if cohort else 0.0
        series = await machine_daily_series(session, target.asset_number, days=84)

        # Weekly buckets - 84 daily points would dominate the context.
        weekly = [
            {
                "week_ending": str(series[i + 6].business_date),
                "win_dollars": round(sum(p.actual_win_cents for p in series[i : i + 7]) / 100, 2),
            }
            for i in range(0, len(series) - 6, 7)
        ][-12:]

        flag = next((f for f in detect_data_quality(machines) if f.asset_number == asset), None)
        return ToolResult(
            {
                "machine": _machine_row(target),
                "cabinet": target.cabinet,
                "manufacturer": target.manufacturer,
                "par_hold_pct": round(target.par_hold_pct * 100, 2),
                "peer_average_wpupd_dollars": peer_avg,
                "weekly_win_trend": weekly,
                "data_quality_flag": (
                    {"issue": flag.issue, "detail": flag.detail} if flag else None
                ),
            },
            f"{asset} ({target.title}) peer index {target.peer_index:.2f}.",
        )

    # ── Top performers ─────────────────────────────────────────────────────
    if name == "get_top_performers":
        tops = await find_top_performers(session, days=days, limit=limit)
        return ToolResult(
            {
                "window_days": days,
                "machines": [_machine_row(t.machine) for t in tops],
                "_note": "Machines with data-quality flags are excluded from this list.",
            },
            f"Top {len(tops)} performers over {days}d.",
        )

    # ── Data quality ───────────────────────────────────────────────────────
    if name == "get_data_quality_flags":
        flags = detect_data_quality(await machine_metrics(session, days=days))
        return ToolResult(
            {
                "window_days": days,
                "total": len(flags),
                "flags": [
                    {
                        "asset_number": f.asset_number,
                        "title": f.title,
                        "zone": f.zone_code,
                        "issue": f.issue,
                        "observed_hold_pct": round(f.observed_hold_pct * 100, 2),
                        "par_hold_pct": round(f.par_hold_pct * 100, 2),
                        "deviation_ratio": f.deviation_ratio,
                        "detail": f.detail,
                    }
                    for f in flags[:limit]
                ],
            },
            f"{len(flags)} data-quality flag(s) over {days}d.",
        )

    raise ValueError(f"Unknown tool: {name}")


__all__ = ["MAX_ROWS", "TOOL_SCHEMAS", "ToolResult", "dispatch"]
