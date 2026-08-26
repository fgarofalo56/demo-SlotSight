---
name: spec-new
description: Write a new feature specification in specs/NNN-name/spec.md. Use when asked to "write a spec", "start a spec", "specify a feature", "create a specification", "spec out" a capability, or when a new feature request arrives that has no spec yet. Covers what and why, never how.
---

# Write a specification

Turn a rough request into a specification precise enough that someone else
could implement it without asking a single question.

> **Portable equivalent of the `/spec-new` prompt file.** Prompt files work only
> in the VS Code Chat view; this skill works there *and* in the Copilot CLI and
> the coding agent. Same instructions.

## The one hard rule

**Write `specs/NNN-name/spec.md` and nothing else.** No source, no tests, no
config. If you catch yourself naming a class, a function, or a file path, stop —
you have drifted from *what* into *how*, and that is the planner's job.

Read anything. Write only under `specs/`.

## Method

**1. Look for prior art first.** Search the codebase. In this repository the
answer to "can we add X" is frequently "X already exists under a different
name" — the analytics layer has more in it than it appears from outside. Say
what you found either way.

**2. Ground it in the real floor** if this is an analytics request. Use the
`slotsight` MCP tools to look at actual numbers. A spec written against real
data beats one written against assumptions, and you will often discover the
premise is wrong.

**3. Ask about anything that would change the design.** Scope, users, and what
"good" looks like — not implementation preferences. One round of questions now
is worth ten during implementation.

**4. Write acceptance criteria a test could be derived from mechanically.**

> ❌ "The floor map should be fast and easy to read."
> ✅ "1. Renders 840 machines in under 500 ms on a 90-day window.
>     2. Each machine is coloured by `peer_index` band, never raw WPUPD.
>     3. Colour is paired with a shape or label so it is legible without colour
>        vision."

**5. Say what is out of scope.** Explicitly. That list prevents more rework than
the in-scope one.

## Structure

```markdown
# NNN — <Title>

**Status:** Draft
**Created:** YYYY-MM-DD

## Problem
What is wrong or missing today, and for whom. Evidence if you have it.

## Users
Who is affected. Be specific: "slot floor manager", not "user".

## Desired outcome
What is true after this ships that is not true now.

## Acceptance criteria
1. Numbered. Independently verifiable. Mechanically testable.

## Out of scope
What this deliberately does not do.

## Open questions
Anything that would change the design if answered differently.

## Constraints
Repository rules that bind this work.
```

## Constraints every spec inherits

From [the constitution](../../../.specify/memory/constitution.md). Restate any
that are load-bearing for this feature:

- Analytics stay **deterministic and LLM-free**. If a spec requires the model to
  compute something, the spec is wrong.
- Rank and colour on **`peer_index`**, never `floor_index`.
- Money is **integer cents**.
- **No player data.** If a request needs PII, say so plainly and stop.
- Anything showing market data must **declare it synthetic**.

## Numbering

Next free `specs/NNN-short-name/`. Check what exists first. Never reuse a number.

## Next

When the spec is written, the next step is to plan it — see the `spec-plan`
skill.
