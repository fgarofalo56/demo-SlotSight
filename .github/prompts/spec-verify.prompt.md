---
name: spec-verify
description: Run every gate and check a spec's acceptance criteria one by one
argument-hint: Spec folder, e.g. 001-slot-floor-analytics-core
agent: agent
tools: ['runCommands', 'search/codebase', 'edit/editFiles']
---

# Verify a spec

Verify `specs/${input:spec:Which spec?}/spec.md` is genuinely satisfied.

## 1. Run every gate, show every output

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
uv run pytest -m golden -v
```

```bash
cd apps/web
pnpm exec tsc --noEmit
pnpm test
pnpm build
```

**Paste the real output.** Not a summary of it. If something fails, that is the
finding — report it and stop pretending otherwise.

## 2. Walk the acceptance criteria individually

For each numbered criterion in `spec.md`, state one of:

- ✅ **Met** — and name the specific gate, test, or command that proves it
- ❌ **Not met** — and say what is missing
- ⚠️ **Unverifiable** — and say why the criterion cannot be checked as written

A criterion is **not** met because the code looks like it should work. It is met
because something ran and passed.

## 3. Check the repository rules

- No credentials or PII introduced anywhere in the diff
- `analytics/` still free of AI and network calls
- `agent/` still reaching data only through `analytics/`
- Money still integer cents; Postgres sums still coerced with `int()`
- Ranking still on `peer_index`
- Market payloads still declaring `is_synthetic`

```bash
gitleaks detect --no-git --redact
```

## 4. Report

Give me a table: criterion → status → evidence.

Then one plain sentence: **is this spec done, or not?** If any criterion is
unmet, the answer is "not", regardless of how much of it works.

Do not mark anything complete in `spec.md` that you have not proven here.
