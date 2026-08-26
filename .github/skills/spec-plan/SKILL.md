---
name: spec-plan
description: Turn an approved spec into plan.md and tasks.md. Use when asked to "plan a spec", "create an implementation plan", "break down a spec into tasks", "how should we build this", or when a spec.md exists and needs a plan. Produces architecture, files, alternatives considered, risks, and an ordered task list.
---

# Plan an implementation

Read `specs/NNN-name/spec.md` and produce `plan.md` and `tasks.md` alongside it.
Write those two files and nothing else — no source, no tests.

> **Portable equivalent of the `/spec-plan` prompt file.** Prompt files work only
> in the VS Code Chat view; this skill works there *and* in the Copilot CLI and
> the coding agent.

## Before planning

- **Open every file you intend to change.** Do not plan against a memory of the
  codebase.
- **Check current library APIs** with the `context7` MCP server. SQLAlchemy 2.0,
  Pydantic v2, FastAPI, React 19, and Tailwind v4 all changed idioms recently. A
  plan built on a stale API wastes the implementer's day.
- **Check Azure guidance** with `microsoft-docs` if this touches infra.

## plan.md

```markdown
# Plan — NNN <Title>

## Approach
Two or three paragraphs. What is the shape of the change?

## Architecture
Where it sits. A Mermaid diagram if the data flow is not obvious.

## Files
| File | Change | Why |
|---|---|---|

## Alternatives considered
| Option | Why not |
|---|---|

The section readers return to in six months. Be specific about what you
rejected and what would change your mind.

## Risks
What could break. **Call out anything that could affect the golden tests.**

## Verification
Exactly which gate proves each acceptance criterion.
```

## tasks.md

Each task independently completable and verifiable, stating what "done" means
in terms a command can check.

```markdown
- [ ] **T1 — <short title>**
      Files: `path/one.py`, `path/two.py`
      Done when: <a condition a command can verify>
      Verify: `cd apps/api && uv run pytest tests/test_x.py -v`
```

**Sequence tasks that touch the same file.** Two "parallel" tasks editing one
module is a merge conflict you scheduled deliberately.

**Leave the build green after every task.** A task that ends red is two tasks.

## Planning rules for this repository

**Analytics first, then presentation.** A feature that needs a new number needs
a new function in `analytics/` with its own unit test *before* anything in
`routers/`, `agent/`, or `apps/web/` touches it. The agent must never compute.

**A new agent capability is a new tool, not a longer prompt.** Plan a
deterministic function plus a tool schema in `agent/tools.py`. Do not plan
prompt changes as the mechanism.

**Golden tests are load-bearing.** If the plan changes a threshold, the
generator, or a ranking rule, say so under Risks and add a task to re-verify
`pytest -m golden`.

**Money stays integer cents.** Any task introducing a new monetary field
specifies `BigInteger` and where the single conversion to dollars happens.

## Next

Then implement one task at a time — see the `spec-implement` skill.
