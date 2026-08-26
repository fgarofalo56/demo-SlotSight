"""The tool-calling loop.

Flow:

    user question
      -> model picks tools from agent.tools.TOOL_SCHEMAS
      -> we execute them against slotsight.analytics (deterministic)
      -> results go back to the model
      -> model writes prose over numbers it did not choose

The model's job is phrasing and selection. It never computes and never queries.
If it makes something up, the tool-call record returned alongside the answer
shows exactly which functions ran and with what arguments — so the claim is
auditable rather than merely plausible.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.agent.azure_openai import get_client
from slotsight.agent.tools import TOOL_SCHEMAS, dispatch
from slotsight.config import Settings
from slotsight.market import MarketIntelProvider

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = """\
You are SlotSight, the slot floor performance analyst for {property_name}.

You are speaking to slot operations staff — directors, floor managers, and \
analysts. They know the business. Do not explain what coin-in is.

## Where your numbers come from

You have tools that call a deterministic analytics engine over the property's \
own meter data. **Every figure you state must come from a tool result.** You do \
not estimate, extrapolate, or recall figures. If a tool did not return it, you \
do not know it — say so and offer to look it up.

## How to answer

Lead with the answer. Then the evidence. Then, if warranted, the recommendation.

- **Be specific.** Name asset numbers, bank IDs, and titles. "Bank NP-214" beats \
"some penny machines".
- **Quantify against peers, not the floor.** A machine's `peer_index` compares it \
to the same denomination and game type. `floor_index` compares it to everything, \
which mostly just sorts by denomination — mention it only to explain why it \
misleads.
- **Give the window.** "over the last 30 days" — a number without a window is not \
a fact.
- **Be brief.** Three to six sentences for most questions. Use a short markdown \
table when comparing more than three items. No preamble, no "Great question".

## Things you must always do

**Flag synthetic market data.** Market benchmarks and competitor sightings in \
this system are generated for demonstration, not sourced from any real provider. \
When you cite them, say so plainly — once, briefly, not as a disclaimer paragraph.

**Respect data-quality flags.** A machine reporting hold far above its paytable \
par is almost certainly a metering fault, not a star performer. Never recommend \
buying more of one. If a user asks about such a machine, lead with the fault.

**Say when nothing is wrong.** If an area is healthy, say so directly. Do not \
manufacture a concern to seem useful.

**Distinguish variance from decline.** A single weak window is not evidence. The \
tools already confirm findings against a prior window and mark them `sustained` — \
respect that field. If something is flagged but not sustained, call it a watch \
item, not a problem.

**Recommend measurement.** A conversion recommendation is a hypothesis. Impact \
estimates assume only part of an observed market edge transfers to this floor. \
Say the estimate is an estimate, and that post-install measurement replaces it.

## What you will not do

You have no player data — no names, no loyalty accounts, no session tracking. \
This system models machines and money, never people. If asked about players, say \
that plainly.

You cannot change anything. You are read-only: you analyze and recommend, and a \
human decides.
"""


@dataclass
class ToolCallLog:
    tool: str
    arguments: dict[str, Any]
    result_summary: str


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCallLog]
    grounded: bool


# ═══════════════════════════════════════════════════════════════════════════
# Model-family parameter compatibility
# ═══════════════════════════════════════════════════════════════════════════
#
# Azure OpenAI deployments do not accept a uniform parameter set:
#
#   gpt-4.1, gpt-4o     want `max_tokens`,  accept `temperature`
#   gpt-5.x, o-series   want `max_completion_tokens`, reject non-default
#                       `temperature` outright
#
# This is a public teaching repo, so whoever clones it will point at whatever
# deployment they happen to have. A hardcoded model-name allowlist would be
# wrong for somebody on day one and stale for everybody within a quarter.
#
# Instead we send the modern shape and let the API tell us what it dislikes:
# Azure returns a structured 400 naming the offending parameter, so we drop
# exactly that one and retry. Self-correcting, and it needs no maintenance
# when the next model family lands.

_MAX_PARAM_RETRIES = 4

# Swap rather than drop, where an equivalent exists.
_PARAM_FALLBACKS: dict[str, str | None] = {
    "max_completion_tokens": "max_tokens",
    "max_tokens": "max_completion_tokens",
    "temperature": None,
    "top_p": None,
    "tool_choice": None,
}


_UNSUPPORTED_CODES = frozenset({"unsupported_parameter", "unsupported_value"})


def _unsupported_param(exc: BadRequestError) -> str | None:
    """Extract the offending parameter name from an Azure OpenAI 400, if any.

    The openai SDK *unwraps* the ``{"error": {...}}`` envelope, so ``exc.body``
    is the inner error object and exposes ``code``/``param`` at the top level.
    It also surfaces both as attributes on the exception. We check the
    attributes first, then both body shapes, because getting this wrong fails
    silently - the retry simply never fires and you are left staring at a 400
    that looks unhandled.
    """
    code = getattr(exc, "code", None)
    param = getattr(exc, "param", None)
    if isinstance(code, str) and code in _UNSUPPORTED_CODES and isinstance(param, str):
        return param

    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None

    # Flat shape (what the SDK actually hands us) and nested shape (raw wire).
    for candidate in (body, body.get("error")):
        if not isinstance(candidate, dict):
            continue
        c, p = candidate.get("code"), candidate.get("param")
        if isinstance(c, str) and c in _UNSUPPORTED_CODES and isinstance(p, str):
            return p

    return None


async def _create_completion(
    client: Any, deployment: str, messages: list[dict[str, Any]], **kwargs: Any
) -> Any:
    """chat.completions.create with automatic parameter-shape negotiation."""
    attempt: dict[str, Any] = dict(kwargs)

    for _ in range(_MAX_PARAM_RETRIES):
        try:
            return await client.chat.completions.create(
                model=deployment, messages=messages, **attempt
            )
        except BadRequestError as exc:
            param = _unsupported_param(exc)
            if param is None or param not in attempt:
                raise

            value = attempt.pop(param)
            replacement = _PARAM_FALLBACKS.get(param)
            if replacement and replacement not in attempt:
                attempt[replacement] = value
                logger.info(
                    "Deployment %r rejected %r; retrying with %r",
                    deployment,
                    param,
                    replacement,
                )
            else:
                logger.info("Deployment %r rejected %r; retrying without it", deployment, param)

    # Last resort: the bare minimum every model family accepts.
    return await client.chat.completions.create(model=deployment, messages=messages)


async def run_conversation(
    message: str,
    session: AsyncSession,
    market: MarketIntelProvider,
    settings: Settings,
    window_days: int = 30,
) -> AgentResult:
    """Run one question through the tool-calling loop."""
    client = get_client(settings)
    deployment = settings.azure_openai_deployment or ""

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(property_name=settings.property_name),
        },
        {
            "role": "user",
            "content": (
                f"{message}\n\n"
                f"(Unless the question implies otherwise, use a {window_days}-day window.)"
            ),
        },
    ]

    call_log: list[ToolCallLog] = []

    for round_index in range(MAX_TOOL_ROUNDS):
        response = await _create_completion(
            client,
            deployment,
            messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=1_600,
        )

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls

        if not tool_calls:
            return AgentResult(
                answer=(choice.message.content or "").strip(),
                tool_calls=call_log,
                grounded=bool(call_log),
            )

        messages.append(
            {
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            try:
                result = await dispatch(name, args, session, market, default_window=window_days)
                payload, summary = result.payload, result.summary
            except Exception as exc:
                logger.warning("Tool %s failed: %s", name, exc, exc_info=True)
                payload = {"error": f"{type(exc).__name__}: {exc}"}
                summary = f"{name} failed: {type(exc).__name__}"

            call_log.append(ToolCallLog(tool=name, arguments=args, result_summary=summary))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(payload, default=str),
                }
            )

        logger.debug("Tool round %d complete (%d calls)", round_index + 1, len(tool_calls))

    # Ran out of rounds - ask for a final answer with no further tools.
    final = await _create_completion(
        client,
        deployment,
        messages,
        temperature=0.2,
        max_completion_tokens=1_600,
    )
    return AgentResult(
        answer=(final.choices[0].message.content or "").strip(),
        tool_calls=call_log,
        grounded=bool(call_log),
    )


__all__ = ["MAX_TOOL_ROUNDS", "SYSTEM_PROMPT", "AgentResult", "ToolCallLog", "run_conversation"]
