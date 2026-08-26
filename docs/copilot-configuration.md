# 🤖 Copilot configuration

Every way this repository configures GitHub Copilot in VS Code, what each one
does, and — more usefully — **why it is written the way it is**.

Copy any of it. That is the point.

---

## The map

```
.github/
├── copilot-instructions.md      always in context
├── instructions/                7 files, scoped by applyTo glob
├── prompts/                     8 slash commands
├── agents/                      6 custom agents with handoffs
├── skills/                      2 skills, loaded on demand
└── hooks/                       4 lifecycle hooks
AGENTS.md                        agent-host entry point
.vscode/mcp.json                 5 MCP servers
```

| Mechanism | Loaded | Best for |
|---|---|---|
| `copilot-instructions.md` | Always | Rules that must never be violated |
| `AGENTS.md` | Always (agent hosts) | Short pointer for non-VS-Code agents |
| `*.instructions.md` | When a matching file is in context | Language and layer conventions |
| `*.prompt.md` | On `/command` | Repeatable multi-step workflows |
| `*.agent.md` | On selection or delegation | A persona with a restricted toolset |
| `SKILL.md` | When the model judges it relevant | Deep domain knowledge |
| Hooks | On lifecycle events | Enforcement — the only one that *executes* |
| MCP | Always available as tools | Live external data |

**The distinction that matters:** instructions, prompts, agents, and skills all
*inform*. Only hooks *enforce*. If a rule must hold even when the model is
having a bad day, it needs a hook.

---

## 1. Repository instructions

**[`.github/copilot-instructions.md`](../.github/copilot-instructions.md)** — in
context for every request.

It carries five rules, and the reason it stops there is that this file competes
for attention with the user's actual question. A 400-line instructions file is
an instructions file the model skims.

Each rule states the **failure it prevents**, not just the behaviour it wants:

> **Money is integer cents; ratios are floats.**
> Floating-point money accumulates error across a 180-day × 840-machine
> aggregation, and this is precisely the domain where a rounding drift becomes a
> wrong business recommendation.
>
> ⚠️ Postgres `SUM()` over `BIGINT` returns `NUMERIC`, which asyncpg gives you
> as `decimal.Decimal`. Coerce with `int()`. This fails **only** against
> Postgres — the SQLite tests stay green.

That last paragraph is worth more than the rule above it. It is a specific trap
that cost real time, and it now costs nobody anything.

**[`AGENTS.md`](../AGENTS.md)** is the short version, for agent hosts that read
it instead.

---

## 2. Path-scoped instructions

**[`.github/instructions/`](../.github/instructions/)** — seven files, each with
an `applyTo` glob, loaded only when a matching file is in context.

```yaml
---
name: Python conventions
description: Python style, typing, async, and the money/Decimal gotcha
applyTo: "**/*.py"
---
```

| File | `applyTo` | Carries |
|---|---|---|
| `python` | `**/*.py` | Typing, async, the `Decimal` trap |
| `react` | `apps/web/**/*.{ts,tsx,css}` | The peer-index colour scale, a11y |
| `tests` | `**/tests/**,**/*.test.*` | Why golden tests must not be silenced |
| `bicep` | `infra/**/*.bicep` | RBAC-not-keys, cost defaults |
| `data-model` | `models/**,seed/**` | Schema rules, generator tuning traps |
| `security` | `**` | Credentials, PII, synthetic disclosure |
| `docs` | `**/*.md` | Voice and formatting |

Scoping is what makes these worth writing. The React file can be opinionated
about Tailwind tokens because it never loads while you are editing Python.

---

## 3. Prompt files — slash commands

**[`.github/prompts/`](../.github/prompts/)** — eight, invoked as `/name`.

```yaml
---
name: spec-plan
description: Turn an approved spec into an implementation plan and ordered tasks
argument-hint: The spec folder, e.g. 003-competitive-intel-feed
agent: Spec Planner
tools: ['search/codebase', 'edit/editFiles', 'context7/*', 'microsoft-docs/*']
---
```

`${input:spec:Which spec?}` prompts for an argument. `#tool:context7` references
a tool inline. `agent:` pins the prompt to a specific custom agent.

The spec flow: `/spec-new` → `/spec-clarify` → `/spec-plan` → `/spec-implement`
→ `/spec-verify`. Plus `/add-metric`, `/explain-floor`, `/deploy-azure`.

**Prompts encode the *order* of a workflow.**
[`/add-metric`](../.github/prompts/add-metric.prompt.md) exists because there is
a right sequence for adding a metric — pure function, unit test, aggregation,
API, *then* the agent tool — and doing it out of order produces a metric the
assistant can hallucinate.

---

## 4. Custom agents

**[`.github/agents/`](../.github/agents/)** — six, each a persona with a
**restricted toolset**.

| Agent | Tools | Restriction that matters |
|---|---|---|
| Spec Architect | read + `edit` | May only write under `specs/` |
| Spec Planner | read + `edit` + docs MCP | Writes `plan.md` / `tasks.md` only |
| Implementer | full edit + `runCommands` | Can delegate to Code Reviewer |
| **Code Reviewer** | **read + run only** | **No edit tools at all** |
| Slot Analyst | `slotsight/*` only | Read-only domain expert |
| Azure Deployer | `azure/*` + docs | Must confirm before changing cloud state |

**The Code Reviewer having no edit tools is the design decision worth copying.**
A reviewer that can edit stops reviewing and starts implementing, and then
nobody has reviewed the result.

### Handoffs

```yaml
handoffs:
  - label: 'Plan this spec'
    agent: Spec Planner
    prompt: 'Read the spec I just wrote and produce plan.md.'
    send: false
```

Each agent offers a button for the next stage. `send: false` pre-fills the
prompt without submitting, so you can adjust it — which you usually want to.

The chain: **Architect → Planner → Implementer → Reviewer → back to
Implementer.**

### Subagents

```yaml
agents: ['Code Reviewer']
```

The Implementer may delegate to the Code Reviewer. Restricting the allowlist to
one name is deliberate — `'*'` produces agents calling agents in ways nobody
predicted.

---

## 5. Agent skills

**[`.github/skills/`](../.github/skills/)** — `<name>/SKILL.md`, loaded when the
model judges the description relevant.

Skills hold **knowledge**; instructions hold **rules**. The line: if a competent
engineer new to the domain would need it explained, it is a skill.

| Skill | Holds |
|---|---|
| `slot-floor-analytics` | WPUPD, hold, par, and the four reasoning traps |
| `neon-palms-design-system` | Tokens, the peer-index colour scale, a11y |

The `description` frontmatter is the whole retrieval mechanism — the model reads
only that when deciding whether to load the body. A vague description produces a
skill that never loads.

---

## 6. Hooks — the only thing that enforces

**[`.github/hooks/guardrails.json`](../.github/hooks/guardrails.json)**

```json
{
  "hooks": {
    "PreToolUse": [
      { "type": "command", "command": "python .github/hooks/scripts/guard_secrets.py", "timeout": 10 }
    ]
  }
}
```

| Event | Script | Does |
|---|---|---|
| `SessionStart` | `inject_context.py` | Emits branch, spec status, stack health |
| `PreToolUse` | `guard_secrets.py` | **Denies** credential reads and destructive commands |
| `PostToolUse` | `format_and_lint.py` | Runs `ruff format` on touched files |
| `Stop` | `verify_gates.py` | Warns if source changed but gates never ran |

### The guardrail

VS Code passes the event as JSON on stdin. Emitting a `deny` decision blocks
**that single tool call** while leaving the session alive, so the agent can read
the reason and choose differently:

```python
print(json.dumps({
    "hookSpecificOutput": {
        "permissionDecision": "deny",
        "permissionDecisionReason": f"{reason}\n\n{suggestion}",
    }
}))
```

It blocks reads of `.env`, `secrets/**`, `*.pem`, `*.key`, and commands like
`rm -rf`, `git push --force`, `DROP DATABASE`, and `git commit --no-verify`.

**Three things about it are worth stealing:**

**It fails open.** Malformed input exits 0 without denying. A guard that crashes
into "block everything" is a guard someone deletes by lunchtime.

**Every denial names an alternative.** A block with no route forward just gets
worked around.

**It has [47 tests](../apps/api/tests/test_hooks.py).** The first version looked
correct and let `secrets/prod.json` straight through — the pattern required a
path separator before `secrets`, and in the serialized tool input the preceding
character is a quote. **A guard with a hole in it is worse than no guard,
because it is trusted.**

### Why the scripts are Python, not shell

They run on whatever the contributor has. Python is already a dependency; a
`.sh` hook breaks on Windows and a `.ps1` breaks everywhere else.

---

## 7. MCP servers

**[`.vscode/mcp.json`](../.vscode/mcp.json)** — five servers, **zero committed
secrets**.

| Server | Type | Gives Copilot |
|---|---|---|
| `github` | http | Issues, PRs, Actions — VS Code handles OAuth |
| `microsoft-docs` | http | Official Azure docs, no auth |
| `context7` | http | Version-accurate library docs |
| `azure` | stdio | Live Azure resources |
| **`slotsight`** | stdio | **The live slot floor** |

### Secrets stay out of the file

```json
"inputs": [
  {
    "id": "context7-api-key",
    "type": "promptString",
    "password": true
  }
],
"servers": {
  "context7": {
    "headers": { "Authorization": "Bearer ${input:context7-api-key}" }
  }
}
```

VS Code prompts once and stores it in the OS credential manager. The repository
never sees it.

### Our own server

[`mcp_server.py`](../apps/api/src/slotsight/mcp_server.py) exposes seven tools
over the live database — and reuses the **exact dispatch** the chat endpoint
uses:

```
REST API   ─┐
/api/chat  ─┼─→ agent.tools.dispatch ─→ analytics/ ─→ PostgreSQL
MCP server ─┘
```

One implementation, three surfaces. The fastest way to lose trust in an
analytics product is for the dashboard and the assistant to disagree about the
same question, and the only reliable prevention is making a second
implementation impossible.

More: [MCP servers](mcp-servers.md)

---

## What I would tell you to copy first

1. **The `PreToolUse` guardrail.** Highest value per line in the repo, and the
   layer most repositories lack entirely.
2. **A read-only reviewer agent.** One frontmatter field, real behavioural change.
3. **Instructions that name the failure, not the rule.** "Coerce with `int()`
   because Postgres returns `Decimal` and it only breaks in production" beats
   "use integers".
4. **Prompt files for workflows with a required order.** Anywhere the sequence
   matters more than the steps.
5. **An MCP server over your own domain.** Copilot answering questions about
   your live data, while you write code against it, changes how the tool feels.
