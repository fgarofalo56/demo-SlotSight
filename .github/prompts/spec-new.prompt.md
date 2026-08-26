---
name: spec-new
description: Start a new feature specification from a rough idea
argument-hint: A one-line description of what you want
agent: Spec Architect
tools: ['search/codebase', 'search/usages', 'vscode/askQuestions', 'edit/editFiles', 'slotsight/*']
---

# Create a new specification

Turn this request into a rigorous spec:

**${input:request:What do you want SlotSight to do?}**

## Steps

1. **Look for prior art first.** Search the codebase. In this repository the
   answer to "can we add X" is frequently "X already exists under a different
   name" — the analytics layer has more in it than it appears from outside.
   Say what you found either way.

2. **Ground it in the real floor** if this is an analytics request. Use the
   `slotsight` tools to look at actual numbers. A spec written against real data
   beats one written against assumptions, and you will often discover the
   premise is wrong.

3. **Ask about anything that would change the design.** Use
   `#tool:vscode/askQuestions`. Scope, users, and what "good" looks like — not
   implementation preferences. One round of questions now is worth ten during
   implementation.

4. **Pick the next free number.** Check `specs/` and use
   `specs/NNN-short-name/`. Never reuse a number.

5. **Write `spec.md`** following the structure in
   [`../instructions/specs.instructions.md`](../instructions/specs.instructions.md).

## Remember

- **What and why. Never how.** No class names, no file paths, no libraries. If
  you are naming a module, you have drifted into planning.
- **Acceptance criteria must be mechanically testable.** "Fast" is not a
  criterion. "Under 500 ms for a 90-day window" is.
- **Write the out-of-scope list.** It prevents more rework than the in-scope one.
- Restate any repository constraints that bind this feature: peer-index ranking,
  integer cents, no PII, analytics stay LLM-free, synthetic data self-declares.

When you are done, show me the acceptance criteria and the open questions before
anything else.
