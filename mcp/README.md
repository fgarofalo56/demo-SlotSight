# The SlotSight MCP server

**The implementation lives at
[`apps/api/src/slotsight/mcp_server.py`](../apps/api/src/slotsight/mcp_server.py).**

It is inside the API package on purpose. The server calls
`slotsight.agent.tools.dispatch` — the exact same function the `/api/chat`
endpoint calls — which in turn calls `slotsight.analytics`.

```
REST API   ─┐
/api/chat  ─┼─→ agent.tools.dispatch ─→ analytics/ ─→ PostgreSQL
MCP server ─┘
```

Keeping it in a separate top-level package would have meant either duplicating
that code or importing across package boundaries with a path hack. One
implementation, three surfaces — the UI, the assistant, and Copilot cannot drift
into quoting different numbers for the same question, because a second
implementation does not exist.

## Running it

Configured in [`.vscode/mcp.json`](../.vscode/mcp.json). Needs the database up:

```bash
docker compose up -d db
make seed
```

Standalone:

```bash
uv run --project apps/api slotsight-mcp
```

It speaks MCP over stdio. Logs go to stderr, because **stdout is the protocol
transport** and a stray print corrupts the stream.

## The seven tools

| Tool | Answers |
|---|---|
| `get_floor_summary` | How is the floor doing? |
| `find_underperformers` | What is fading? |
| `get_recommendations` | What should we do? |
| `compare_to_market` | What is hot that we don't run? |
| `get_machine_detail` | Tell me about NP-21401 |
| `get_top_performers` | What is working? |
| `get_data_quality_flags` | Is the data reliable? |

Full write-up, including how to build your own:
**[docs/mcp-servers.md](../docs/mcp-servers.md)**
