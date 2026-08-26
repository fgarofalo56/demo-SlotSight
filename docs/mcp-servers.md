# 🔌 MCP servers

Five Model Context Protocol servers, configured in
[`.vscode/mcp.json`](../.vscode/mcp.json). One of them this repository builds.

---

## What MCP is for

Without it, Copilot knows your open files and its training data. With it, Copilot
can call live tools: read your GitHub issues, look up an Azure API version that
shipped last month, or query your production analytics.

The shift is from *"generate plausible code"* to *"answer using current facts"*.

---

## The five

| Server | Transport | Auth | Gives Copilot |
|---|---|---|---|
| [`github`](#github) | http | OAuth (automatic) | Issues, PRs, Actions, code search |
| [`microsoft-docs`](#microsoft-docs) | http | none | Official Microsoft/Azure documentation |
| [`context7`](#context7) | http | optional key | Version-accurate library docs |
| [`azure`](#azure) | stdio | your `az login` | Live Azure resources |
| [`slotsight`](#slotsight-ours) | stdio | none (local db) | **The live slot floor** |

---

## Secrets never touch the config file

One server takes an API key. It is not in the repository:

```json
"inputs": [
  {
    "id": "context7-api-key",
    "type": "promptString",
    "title": "Context7 API key",
    "password": true
  }
],
"servers": {
  "context7": {
    "type": "http",
    "url": "https://mcp.context7.com/mcp",
    "headers": { "Authorization": "Bearer ${input:context7-api-key}" }
  }
}
```

VS Code prompts once and stores it in the OS credential manager. `password: true`
masks it. **The repository never sees the value.**

The other four need no stored credential at all — `github` uses VS Code's OAuth,
`azure` inherits your `az login` session, `microsoft-docs` is public, and
`slotsight` talks to a local database.

---

## `github`

```json
"github": { "type": "http", "url": "https://api.githubcopilot.com/mcp/" }
```

Ask *"what open issues mention the peer index?"* and it searches your actual
repository. Also PRs, Actions runs, and code search.

Scopable by URL path — `/mcp/readonly` or `/mcp/x/repos` — if you want a
narrower toolset than the default.

## `microsoft-docs`

```json
"microsoft-docs": { "type": "http", "url": "https://learn.microsoft.com/api/mcp" }
```

Three tools: `microsoft_docs_search`, `microsoft_docs_fetch`,
`microsoft_code_sample_search`.

**Use this before writing Bicep.** Azure API versions change frequently enough
that a model recalling one is a coin flip, and copying a version from an old
sample is how you end up debugging a schema error that has nothing to do with
your change.

## `context7`

```json
"context7": { "type": "http", "url": "https://mcp.context7.com/mcp" }
```

Version-accurate library documentation. This repo uses SQLAlchemy 2.0,
Pydantic v2, React 19, and Tailwind v4 — **all four changed idioms recently**,
and all four have enormous volumes of outdated examples in any training set.

Ask for "SQLAlchemy async session pattern" and you get the 2.0 answer rather
than the 1.4 one.

The key is optional; without it you are rate-limited.

## `azure`

```json
"azure": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@azure/mcp@latest", "server", "start"]
}
```

Live Azure. List resource groups, inspect Container Apps logs, check pricing,
run `azd` operations — all through chat, authenticated by your existing
`az login`.

Paired with the [Azure Deployer](../.github/agents/azure-deployer.agent.md)
agent, which is required to confirm before anything that changes cloud state.

## `slotsight` (ours)

```json
"slotsight": {
  "type": "stdio",
  "command": "uv",
  "args": ["run", "--project", "apps/api", "slotsight-mcp"],
  "env": { "POSTGRES_HOST": "localhost", "POSTGRES_PORT": "5432" }
}
```

**This is the interesting one.** Seven tools over the live slot floor:

| Tool | Answers |
|---|---|
| `get_floor_summary` | How is the floor doing? |
| `find_underperformers` | What is fading? |
| `get_recommendations` | What should we do? |
| `compare_to_market` | What is hot that we don't run? |
| `get_machine_detail` | Tell me about NP-21401 |
| `get_top_performers` | What is working? |
| `get_data_quality_flags` | Is the data reliable? |

Ask in Copilot Chat, while writing code:

> *"Which banks are fading, and is High Limit healthy?"*

And it queries PostgreSQL — not its imagination.

### Why it reuses the chat dispatch

```
REST API   ─┐
/api/chat  ─┼─→ agent.tools.dispatch ─→ analytics/ ─→ PostgreSQL
MCP server ─┘
```

[`mcp_server.py`](../apps/api/src/slotsight/mcp_server.py) calls the **exact
same function** the chat endpoint calls. It reimplements nothing.

The fastest way to lose trust in an analytics product is for the dashboard and
the assistant to quote different numbers for the same question, and the only
reliable way to prevent it is to make a second implementation impossible.

---

## Building your own

Under 200 lines with the Python SDK.

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="slotsight",
    instructions=(
        "Compare machines using peer_index, which benchmarks against the same "
        "denomination and game type. Do NOT use floor_index for ranking."
    ),
)

@mcp.tool()
async def find_underperformers(window_days: int = 30, limit: int = 10) -> str:
    """Banks trailing their peer cohort, confirmed against a prior window.

    Short-run variance will not trigger a flag. Machines with data-quality
    problems are already excluded.
    """
    return await _call("find_underperformers", {...})

def main() -> int:
    mcp.run(transport="stdio")
```

> [!WARNING]
> **MCP Python SDK 2.x renamed `FastMCP` to `MCPServer`.** The decorator and run
> APIs are otherwise unchanged. Pin `mcp>=2` — on 1.x the import fails with a
> clear migration message rather than something subtle.

### Four things worth knowing

**1. `stdout` is the transport.** A stray `print()` corrupts the protocol stream
in a way that is genuinely unpleasant to debug. Log to `stderr`:

```python
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
```

**2. Docstrings are the interface.** The model reads them to decide whether to
call your tool. A vague docstring produces a tool that never fires, or fires for
the wrong question. Write them for someone who does not know your domain.

**3. Truncate hard.** 840 machines of detail exhausts the context window and
degrades the answer. Return the rows that matter plus the counts you omitted, so
the model can describe the rest honestly.

**4. Surface errors, never crash.** Return a payload with an `error` field and a
hint. The model can then tell the user something useful:

```python
except Exception as exc:
    return json.dumps({
        "error": f"{type(exc).__name__}: {exc}",
        "hint": "Is the database up and seeded? Try: docker compose up -d db && make seed",
    })
```

---

## When servers do not connect

1. **Reload the window.** `.vscode/mcp.json` is read at startup.
2. **`slotsight` needs the database.** `make up` or `make dev`.
3. **`azure` downloads on first run** via `npx`. Give it a minute.
4. **`context7` prompts for a key.** Optional — press Escape.
5. Check the MCP output channel for the real error.

More: [troubleshooting](troubleshooting.md#mcp-servers-show-as-unavailable-in-vs-code)
