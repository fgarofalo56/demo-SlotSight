---
name: spec-implement
description: Implement one task from a spec's tasks.md, with tests, and run the gates. Use when asked to "implement a task", "build the next task", "work on spec NNN", "do task T2", or to continue implementing an existing plan. One task at a time, never two.
---

# Implement one task

Work from `specs/NNN-name/tasks.md`. Implement **the next unchecked task**, or
the specific one named. **One task only** — not two because they are related,
not "while I was in there".

> **Portable equivalent of the `/spec-implement` prompt file.** Prompt files work
> only in the VS Code Chat view; this skill works there *and* in the Copilot CLI
> and the coding agent.

## Scope discipline

If you find something else broken, note it and move on — or add a task for it. A
diff that does more than its task is a diff nobody can review, and it is how an
unrelated regression gets attributed to a feature.

If the task turns out to be wrong or impossible, **stop and say so**. Do not
silently substitute a different task.

## Method

1. **Read the task, the spec's acceptance criteria, and the plan's risks.**
2. **Open the files you will change** and the tests around them. Match the
   surrounding idiom — this codebase has consistent conventions and a foreign
   style is a defect in itself.
3. **Check current APIs** with the `context7` MCP server rather than writing
   from memory. SQLAlchemy 2.0, Pydantic v2, React 19, Tailwind v4.
4. **Write the code and its test together.** Name the test for the behaviour it
   protects, not the function it calls.
5. **Run the gates and show the real output:**

   ```bash
   cd apps/api && uv run ruff check . && uv run mypy src && uv run pytest
   cd apps/web && pnpm exec tsc --noEmit && pnpm exec vitest run
   ```

6. **If you touched `analytics/`, a threshold, or the generator — run the golden
   tests:**

   ```bash
   cd apps/api && uv run pytest -m golden -v
   ```

   If one fails, **do not adjust the assertion to match your output.** Work out
   which behaviour changed and whether that was intended. Those tests are
   designed to be hard to silence.

7. **Check the box** in `tasks.md`.

## Rules that will fail review

- AI or network calls in `analytics/`
- `agent/` querying the database instead of going through `analytics/`
- Money as `float`, or a Postgres `SUM()` without `int()` coercion — that one
  passes the SQLite tests and fails only in production
- Ranking or colouring on `floor_index` instead of `peer_index`
- Any credential, any PII, any Azure OpenAI API-key setting
- Market data without `is_synthetic`

## Report honestly

Say what you actually did, including what failed or what you skipped.
**"It should work now" is not a result** — run it and paste the output. A green
summary over a broken build costs the reviewer more than it saved you.

## Next

When the task list is done, verify against the acceptance criteria — see the
`spec-verify` skill.
