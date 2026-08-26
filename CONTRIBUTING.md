# Contributing

This is a teaching repository. The most valuable contributions make it a
**clearer example**, not a bigger one.

---

## Setup

```bash
git clone https://github.com/fgarofalo56/demo-SlotSight.git
cd demo-SlotSight
make setup      # deps + wires the git hooks
make up
```

`make setup` runs `git config core.hooksPath .githooks`. **Git hooks are opt-in
— cloning does not enable them.** Verify with `make verify-hooks`.

## The loop

1. **Start with a spec** for anything non-trivial — `specs/NNN-name/spec.md`.
   Use `/spec-new` in Copilot Chat.
2. **Plan it** — `/spec-plan`.
3. **Implement one task at a time** — `/spec-implement`.
4. **Run the gates and show the output** — `/spec-verify`.

## The rules

From [the constitution](.specify/memory/constitution.md). Breaking one is a
defect, not a style disagreement.

1. **No secrets, no PII.** Ever. Azure OpenAI uses Entra ID — do not add an
   API-key setting.
2. **`analytics/` stays deterministic.** No AI, no network calls. `agent/`
   reaches data only through it.
3. **Money is integer cents.** Coerce Postgres `SUM()` with `int()`.
4. **Rank on `peer_index`, never `floor_index`.**
5. **Market data declares itself synthetic** in every payload and every view.
6. **Every feature starts as a spec.**

## Gates

Nothing is done until these pass **and you have shown the output**.

```bash
make gates
make test-golden
```

> **"It should work now" is not a result.** A green summary over a broken build
> costs the next person more than it saved you.

## If a golden test fails

**Do not adjust the assertion to match your output.** Those tests assert the
pipeline reaches the right *conclusion* about a floor whose truth we control,
and they are designed to be hard to silence.

Work out which behaviour changed. If the change was intended, update
`seed/scenarios.py` and explain why in the commit — where a reviewer will see it.

## Commits

Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

Reference the spec where there is one: `feat(analytics): add coverage gaps (003)`.

## Pull requests

- One concern per PR
- Gates passing, with output pasted
- Docs updated if behaviour changed
- Spec updated if the implementation revealed the spec was wrong — a spec that
  quietly diverges from the code is worse than no spec

## Things that will be declined

- **A player, patron, or loyalty table.** Permanent. See Constitution VII.
- **An Azure OpenAI API key setting.** Auth is Entra ID.
- **Real market data or a scraper.** See [`NOTICE.md`](NOTICE.md).
- **Ranking on `floor_index`.**
- **Disabling the agent guardrail hook.**
- **Anything that makes the example harder to read for a marginal feature.**
  This repo is read more than it is run.

## Reporting a security issue

Open a [Security Advisory](https://github.com/fgarofalo56/demo-SlotSight/security/advisories/new), not a public issue.
See [`SECURITY.md`](SECURITY.md).
