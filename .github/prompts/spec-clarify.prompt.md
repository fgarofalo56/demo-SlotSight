---
name: spec-clarify
description: Resolve the open questions in a spec before planning starts
argument-hint: Spec folder, e.g. 003-competitive-intel-feed
agent: Spec Architect
tools: ['search/codebase', 'vscode/askQuestions', 'edit/editFiles', 'slotsight/*']
---

# Clarify a spec

Read `specs/${input:spec:Which spec?}/spec.md` and close out its **Open
questions** section.

## Method

1. **Answer what you can from the codebase or the data.** Some open questions
   are only open because nobody looked. Search the code; query the floor with
   `slotsight` tools. Resolving a question with evidence beats asking me.

2. **Ask me the rest** with `#tool:vscode/askQuestions` — but only the ones
   where different answers lead to genuinely different designs. Give me options
   with a recommendation, not an open-ended prompt. A question I can answer with
   "whatever you think" was not worth asking.

3. **Update `spec.md` in place:**
   - Move each resolved question into **Constraints** or **Acceptance criteria**
     as a concrete statement
   - Record *why* it was decided that way, briefly
   - Leave genuinely unresolvable questions in place, marked as accepted risk
   - Set **Status: Clarified** once the section is empty or explicitly deferred

4. **Re-read the acceptance criteria** afterwards. Clarification usually reveals
   at least one criterion that was too vague to test. Tighten it.

## Watch for

**Scope creep disguised as clarification.** If an answer expands the feature,
that is a new spec or an explicit scope change — say so rather than quietly
absorbing it.

**Questions that are really planning decisions.** "Should we cache this?" is not
a spec question. Push it into the plan and remove it from the spec.

Show me the before-and-after of the acceptance criteria when you are done.
