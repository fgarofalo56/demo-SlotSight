# SlotSight Constitution

The principles every spec, plan, and implementation in this repository is bound
by. Where a spec and this document disagree, this document wins.

These are not aspirations. Each one exists because violating it produces a
specific, identifiable failure.

---

## I. The analytics are deterministic

**Every conclusion SlotSight reaches is produced by ordinary code, against
ordinary SQL, covered by ordinary tests.**

`analytics/` contains no AI and makes no network calls. The conversational
layer is a presentation shell over it: it selects which deterministic function
to run and phrases the result. It never computes and never queries.

*Why:* an operator has to be able to reproduce any number the assistant says.
If the model computes, nobody can — not the operator, not a test, not the
person who wrote it. The moment a figure exists only inside a model's output,
the product is unfalsifiable.

*Consequence:* a new assistant capability is a **new deterministic function
plus a tool schema**, never a longer prompt.

---

## II. Every recommendation carries its evidence

No card says "convert this" without the numbers, the comparison group, the
window, and the confidence.

*Why:* a recommendation a floor manager cannot audit is a recommendation they
should not act on — and won't. Unevidenced advice is how an analytics product
gets opened twice and then never again.

---

## III. Compare like with like

Machines are benchmarked against the same denomination and game type
(`peer_index`), never against the whole floor (`floor_index`).

*Why:* floor-wide indexing mostly just sorts by denomination. In this dataset
the High Limit zone reads **3.4× on floor index** and **1.07× on peer index**.
The first number is meaningless and actively misleading; it would make every
penny machine look like a removal candidate.

*Consequence:* `floor_index` is still returned — but only so the UI can show a
reader why it misleads. Nothing ranks, sorts, or colours on it.

---

## IV. Doing nothing is a valid output

The engine explicitly reports healthy areas as needing no action.

*Why:* an engine that only ever flags problems trains people to ignore it. And
silence is ambiguous — a manager cannot tell "checked and fine" from "not
checked". The all-clear is what makes the alarms credible.

---

## V. Say when the data cannot be trusted

Data-quality findings are evaluated **first** and their subjects are removed
from every performance ranking, in both directions.

*Why:* the highest-"winning" machine in this dataset is a metering fault. A
rank-by-win leaderboard puts it first and invites someone to order eight more
of a broken unit. **An analytics tool that cannot say "I don't believe this
number" is not safe to act on.**

---

## VI. Money is exact

Money is stored, summed, and passed as integer cents, converted to dollars
exactly once at the API boundary.

*Why:* floating-point error accumulates across a 180-day × 840-machine
aggregation, and this is precisely the domain where a rounding drift becomes a
wrong business recommendation.

---

## VII. Machines and money — never people

There is no player table, no loyalty ID, no card number, no name, no session
tracking. There never will be.

*Why:* the valuable slot-floor analytics problem is about asset performance and
does not require player data. Collecting PII you do not need is a liability you
chose. **Adding a player table here is a defect, not a feature.**

---

## VIII. No secret is ever committed

No credential in code, config, tests, fixtures, or commit messages. Azure
OpenAI uses Entra ID — there is no API key to leak because the application will
not accept one.

*Why:* a push to a public remote is publication. Force-pushing it away does not
un-publish it.

*Consequence:* four layers — `.gitignore`, local git hooks, an agent guardrail
that blocks Copilot itself, and a CI scan over full history. See
[`SECURITY.md`](../../SECURITY.md).

---

## IX. Synthetic data declares itself

Every payload carrying generated market data sets `is_synthetic: true`, and
every view showing it carries a visible marker.

*Why:* a recommendation built on invented benchmarks must never reach a screen
looking like one built on real market intelligence. See
[`NOTICE.md`](../../NOTICE.md).

---

## X. Verify by measurement, not by assertion

Nothing is "done", "passing", or "shipped" unless a gate actually ran **this
session** and the output was shown.

*Why:* **"it should work now" is not a result.** A green summary over a broken
build costs the next person more than it saved the last one. Three real bugs in
this codebase — a missing async transport, a wrong model parameter name, and an
error envelope that was unwrapped differently than assumed — were found only by
running the thing, and every one of them would have passed a code review.

---

## XI. Every feature starts as a spec

`spec.md` (what and why) → `plan.md` (how) → `tasks.md` (ordered) →
implementation → verification.

*Why:* it is the subject of this repository. But also: the specs are where the
*why* survives after the code changes. A plan's "alternatives considered"
section is the most valuable thing in `specs/`.

---

## Amending this document

Changing a principle requires updating this file **and** stating the change in
the spec that motivated it. Principles that quietly erode were never principles.
