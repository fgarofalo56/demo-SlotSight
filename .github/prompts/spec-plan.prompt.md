---
name: spec-plan
description: Turn an approved spec into an implementation plan and ordered tasks
argument-hint: The spec folder, e.g. 003-competitive-intel-feed
agent: Spec Planner
tools: ['search/codebase', 'search/usages', 'edit/editFiles', 'context7/*', 'microsoft-docs/*']
---

# Plan an implementation

Read `specs/${input:spec:Which spec? e.g. 003-competitive-intel-feed}/spec.md`
and produce `plan.md` and `tasks.md` alongside it.

## Before planning

- **Open every file you intend to change.** Do not plan against a memory of the
  codebase.
- **Check current library APIs with `#tool:context7`.** SQLAlchemy 2.0,
  Pydantic v2, FastAPI, React 19, and Tailwind v4 all changed idioms recently. A
  plan built on a stale API wastes the implementer's day.
- **Check Azure guidance with `#tool:microsoft-docs`** if this touches infra.

## plan.md must contain

- **Approach** — the shape of the change, in prose
- **Architecture** — where it sits; Mermaid diagram if the data flow is not obvious
- **Files** — table of what changes and why
- **Alternatives considered** — what you rejected and what would change your mind
- **Risks** — explicitly including anything that could affect the golden tests
- **Verification** — which gate proves which acceptance criterion

## tasks.md must be ordered and verifiable

```markdown
- [ ] **T1 — <title>**
      Files: `path/one.py`
      Done when: <condition a command can check>
      Verify: `cd apps/api && uv run pytest tests/test_x.py -v`
```

**Sequence tasks that touch the same file.** Two "parallel" tasks editing one
module is a merge conflict you scheduled deliberately.

**Leave the build green after every task.** A task that ends with a red build is
two tasks.

## Architectural rules that shape every plan here

- **Analytics before presentation.** A new number means a new function in
  `analytics/` with a unit test *before* `routers/`, `agent/`, or `apps/web/`
  touch it.
- **A new assistant capability is a new tool, not a longer prompt.** Plan a
  deterministic function plus a schema in `agent/tools.py`.
- **Golden tests are load-bearing.** If the plan moves a threshold, changes the
  generator, or alters ranking, add a task to re-verify `pytest -m golden`.

Show me the risks and the task list when you are done.
