# AGENTS.md

Entry point for coding agents working in **SlotSight** — an AI-assisted slot
floor performance analyst for the fictional Neon Palms Casino Resort, built as a
teaching reference for spec-driven development with GitHub Copilot.

📖 **Full repository instructions:
[`.github/copilot-instructions.md`](.github/copilot-instructions.md)** — read
that first. This file is the short version.

---

## Non-negotiables

1. **No secrets, no PII, ever.** `.env` is gitignored. Azure OpenAI uses Entra
   ID (`DefaultAzureCredential`) — there is no API key and you must not add one.
   This repo has no player data by design. See [SECURITY.md](SECURITY.md).
2. **`analytics/` is deterministic and LLM-free.** `agent/` may reach data only
   through it. The model phrases; the SQL decides.
3. **Money is integer cents.** Convert to dollars once, at the API boundary.
4. **Rank on `peer_index`, never `floor_index`.** Floor-wide indexing just sorts
   by denomination.
5. **Features start as specs** in `specs/NNN-name/`.

## Setup

```bash
make setup     # installs deps and wires .githooks (git hooks are opt-in)
make up        # docker compose: db + api + web
make seed      # regenerate the synthetic floor
```

## Gates

```bash
make gates                       # lint + types + tests, both apps
uv run pytest -m golden -v       # the four planted narrative signals
```

Nothing is done until these pass **and you have shown the output**. "It should
work now" is not a result.

## Layout

| Path | What |
|---|---|
| `apps/api/src/slotsight/analytics/` | **The core.** Deterministic. Start here. |
| `apps/api/src/slotsight/agent/` | Azure OpenAI tool-calling shell |
| `apps/api/src/slotsight/seed/` | Synthetic generator + planted signals |
| `apps/web/` | React + Vite frontend |
| `mcp/` | Our own MCP server over the analytics |
| `specs/` | Spec-driven development artifacts |
| `infra/` | Bicep for `azd up` |

## Everything is fictional

The casino, titles, manufacturers, and market-data providers are invented. Any
payload carrying market data must declare `is_synthetic: true`. See
[NOTICE.md](NOTICE.md).
