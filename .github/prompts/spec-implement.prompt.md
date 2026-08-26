---
name: spec-implement
description: Implement the next unchecked task from a spec's tasks.md
argument-hint: Spec folder, optionally with a task id — "003" or "003 T2"
agent: Implementer
tools: ['search/codebase', 'search/usages', 'edit/editFiles', 'runCommands', 'context7/*']
---

# Implement a task

Work on `specs/${input:spec:Which spec? e.g. 003-competitive-intel-feed}/tasks.md`.

Implement **the next unchecked task**, or the specific one named. **One task
only** — not two because they are related, not "while I was in there".

## Steps

1. **Read the task, the spec's acceptance criteria, and the plan's risks.**
2. **Open the files you will change** and the tests around them. Match the
   surrounding idiom — a foreign style is a defect in itself here.
3. **Check current APIs with `#tool:context7`** rather than writing from memory.
4. **Write the code and its test together.** Name the test for the behaviour it
   protects, not the function it calls.
5. **Run the gates and show the real output:**

   ```bash
   cd apps/api && uv run ruff check . && uv run mypy src && uv run pytest
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

Tell me what you actually did, including what failed or what you skipped.
**"It should work now" is not a result** — run it and paste the output. A green
summary over a broken build costs me more time than it saved you.
