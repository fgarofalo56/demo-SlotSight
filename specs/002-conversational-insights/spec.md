# 002 — Conversational insights

**Status:** Implemented
**Created:** 2026-08-22
**Completed:** 2026-08-25

---

## Problem

Spec 001 produced a defensible analytics layer, but reaching it still means
knowing which endpoint to call and which filters to set. A slot floor manager
does not want to construct a query — they want to ask the question they already
have in their head, on the floor, in the twenty seconds before a meeting.

The obvious implementation is also the dangerous one: hand a language model the
database and let it write SQL. That produces a system where nobody — not the
operator, not a test, not the person who built it — can reproduce a number it
reports. An analytics product whose figures exist only inside a model's output
is unfalsifiable, and unfalsifiable is unusable for a capital decision.

## Users

- **Slot floor manager** — asks in plain English, on a phone, between tasks
- **Slot analyst** — needs to verify any answer before repeating it
- **Director of slot operations** — asks broad questions and needs to trust the
  answer without auditing it every time

## Desired outcome

Natural-language questions about the floor get accurate, specific, evidenced
answers — where **every figure is traceable to a deterministic function that a
test already covers**, and the user can see which functions ran.

## Acceptance criteria

1. `POST /api/chat` accepts a natural-language question and a window, and returns
   a prose answer.
2. The model can **only** reach data through a fixed set of tools that call
   `analytics/`. It cannot write SQL and has no database access of any kind.
3. Every response includes the **tool calls that produced it** — name, arguments,
   and a result summary — so the answer is reproducible through the REST API.
4. A `grounded` flag reports whether at least one analytics call was made. An
   answer produced with no tool call is marked ungrounded and visibly flagged in
   the UI.
5. Tool payloads are truncated so a question about 840 machines does not exhaust
   the context window. Truncation reports the totals it omitted, so the model can
   describe the rest honestly.
6. Auth is Entra ID via `DefaultAzureCredential`. **There is no API-key setting.**
7. When Azure OpenAI is not configured, `/api/chat` returns **503 with actionable
   remediation** naming the missing variables and listing the endpoints that
   still work. Analytics endpoints are unaffected.
8. The system prompt requires the model to state when market data is synthetic,
   to respect data-quality flags, to distinguish variance from decline, and to
   say plainly when nothing is wrong.
9. The same tool dispatch backs an MCP server, so the analytics are reachable
   from Copilot Chat with identical behaviour.
10. Parameter differences between Azure OpenAI model families are handled without
    a hardcoded model allowlist.

## Out of scope

- Multi-turn conversation memory — each question is independent. Deliberate:
  follow-up context is a real feature but it multiplies the ways an answer can
  drift from its evidence.
- Streaming responses
- Any write operation. SlotSight is read-only; it recommends, humans decide.
- Voice input
- Player-level questions — there is no player data, by design

## Open questions

*(All resolved.)*

- ~~Should the model be allowed to compose tool results arithmetically?~~
  **Resolved: no.** If a question needs a number the tools do not return, the
  right fix is a new deterministic function, not model arithmetic. Encoded in
  the system prompt and in `add-metric.prompt.md`.
- ~~How many tool rounds?~~ **Resolved: four**, then a final no-tools call. In
  practice a broad question uses 5–7 calls across two rounds.
- ~~Show tool calls to the user, or keep them internal?~~ **Resolved: show
  them.** Auditability is the entire value proposition; hiding the mechanism
  would undercut it.

## Constraints

- **Constitution I** — the model phrases, the SQL decides
- **Constitution V** — data-quality flags must be respected in prose
- **Constitution VIII** — no API key, anywhere
- **Constitution IX** — synthetic market data declares itself in every answer

---

## Verification

| Criterion | Status | Evidence |
|---|---|---|
| 1 | ✅ | `routers/chat.py`, live call returns prose + table |
| 2 | ✅ | `agent/tools.py` — dispatch calls `analytics/` only; no session passed to the model |
| 3 | ✅ | `ToolCallRecord[]` on every response; surfaced in the UI disclosure |
| 4 | ✅ | `grounded` flag; UI shows an amber warning when false |
| 5 | ✅ | `MAX_ROWS = 12`; payloads carry `total_*` counts |
| 6 | ✅ | `agent/azure_openai.py` — no key setting exists to set |
| 7 | ✅ | `test_returns_503_with_actionable_remediation` |
| 8 | ✅ | `SYSTEM_PROMPT`; verified in live answers |
| 9 | ✅ | `mcp_server.py` reuses `dispatch` — 7 tools |
| 10 | ✅ | `_create_completion` parameter negotiation |

**Gates run 2026-08-25:** `ruff` clean · `mypy` clean · `pytest` 115 passed.

**Live verification** against `gpt-5.6-sol`: *"Which of our penny video slots are
underperforming this month?"* → 7 tool calls, grounded, correct bank
identification with a markdown comparison table.

## What we learned

**Three bugs that only appeared when the thing actually ran**, none of which
would have failed a code review:

1. `azure-identity`'s async credentials need `aiohttp`, which is not one of its
   declared dependencies. Fails at credential construction, on the chat path
   only.
2. `gpt-5.x` rejects `max_tokens` in favour of `max_completion_tokens`, and
   rejects non-default `temperature` outright. A hardcoded model allowlist would
   have been wrong for someone on day one, so the client negotiates instead.
3. The `openai` SDK **unwraps** the `{"error": {...}}` envelope, so the offending
   parameter is at `exc.body["param"]`, not `exc.body["error"]["param"]`. The
   retry logic looked correct and silently never fired.

Each is now a comment where the trap is, and item 3 is why
`_unsupported_param` checks the exception attributes *first*.

**The tool descriptions did more work than the system prompt.** Early versions
had a long prompt and terse tool descriptions, and the model picked the wrong
tool constantly. Moving the domain guidance into the descriptions — where the
model reads it at selection time — fixed it. The prompt shapes *voice*; the
descriptions drive *behaviour*.
