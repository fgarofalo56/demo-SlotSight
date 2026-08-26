---
name: Spec-driven development
description: How to write and work through specs in this repository
applyTo: "specs/**/*.md,.specify/**/*.md"
---

# Spec-driven development

Every non-trivial feature in SlotSight starts as a spec. The artifacts in
`specs/` are not documentation written after the fact — they are the input that
produced the code.

## The flow

```
/spec-new       →  specs/NNN-name/spec.md      WHAT and WHY. No solution.
/spec-clarify   →  resolves open questions in spec.md
/spec-plan      →  specs/NNN-name/plan.md      HOW. Architecture, files, risks.
/spec-tasks     →  specs/NNN-name/tasks.md     Ordered, verifiable work items.
/spec-implement →  code + tests, one task at a time
/spec-verify    →  runs the gates, checks acceptance criteria
```

## spec.md — what and why, never how

A spec describes **the problem and the desired outcome**. It must not name a
library, a class, or a file. If you find yourself writing "add a method to
`FloorService`", you are writing a plan, not a spec.

Required sections:

- **Problem** — what is wrong or missing today, and for whom
- **Users** — who is affected; be specific ("slot floor manager", not "user")
- **Acceptance criteria** — numbered, each independently verifiable
- **Out of scope** — what this deliberately does not do
- **Open questions** — anything that would change the design if answered
  differently

**Acceptance criteria are the contract.** Write them so a test can be derived
mechanically. "Fast" is not a criterion; "responds in under 500 ms for a 90-day
window" is.

## plan.md — how

Architecture, the files that will change, data flow, and the trade-offs
considered. Name the alternatives you rejected and why — that is the section
readers return to six months later.

Must include a **Risks** section. If a change could break the golden tests, say
so here.

## tasks.md — ordered and verifiable

Each task is small enough to complete and verify independently, and states what
"done" means. Tasks that touch the same file are sequenced, never parallelized.

```markdown
- [ ] **T3 — Peer cohort sizing guard**
      Files: `analytics/floor.py`
      Done when: cohorts below `MIN_COHORT_SIZE` fall back to the floor average
      and `peer_cohort_size` is surfaced; `pytest -m golden` still passes.
```

## Numbering

`specs/NNN-short-name/` — zero-padded, sequential, never reused. Keep completed
specs in place. The history of what was specified, and how it changed during
implementation, is the most valuable thing in this directory.

## Keep the spec honest

If implementation reveals the spec was wrong, **update the spec** and note what
changed and why. A spec that quietly diverges from the code is worse than no
spec — it is confidently wrong.

Mark acceptance criteria as met only when a gate proves it. See
[`../../specs/001-slot-floor-analytics-core/`](../../specs/001-slot-floor-analytics-core/)
for a completed worked example, and `003-competitive-intel-feed/` for one that
is deliberately still spec-only.
