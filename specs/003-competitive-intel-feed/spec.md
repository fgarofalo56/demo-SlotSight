# 003 — Competitive intelligence feed

**Status:** Draft
**Created:** 2026-08-25

> [!NOTE]
> **This spec is deliberately unimplemented.**
>
> It exists so you can run the spec-driven workflow live:
>
> ```
> /spec-plan       003-competitive-intel-feed
> /spec-implement  003-competitive-intel-feed
> /spec-verify     003-competitive-intel-feed
> ```
>
> There is no `plan.md` and no `tasks.md` in this folder yet. That is the point —
> `/spec-plan` writes them.

---

## Problem

SlotSight can already tell a floor manager what is underperforming (spec 001) and
recommend a replacement title from market benchmarks (spec 002). What it cannot
do is answer the question that follows immediately after:

> *"What are the properties down the road actually running, and are we behind?"*

The `competitor_offerings` data exists in the database and is exposed through
`GET /api/market/competitors`, but nothing consumes it. It is a table with no
analysis on top: the API returns a flat list of sightings, the UI does not show
it at all, and the conversational layer has no tool that can reach it.

Concretely, three questions are currently unanswerable:

1. **Coverage gaps** — which titles do multiple competitors operate that we do
   not operate at all?
2. **Relative position** — for titles we *do* share, do we run materially fewer
   units than the market?
3. **Promotional context** — a competitor running a title under a promotion is
   weaker evidence of that title's intrinsic performance than one running it
   without.

Today a slot director answers these by walking a rival floor with a notepad.

## Users

- **Director of slot operations** — needs to know whether the floor mix is
  competitive before a quarterly capital conversation
- **Slot floor manager** — wants the conversion recommendation from spec 002 to
  say whether competitors already validated the target title
- **Slot analyst** — needs the comparison to be defensible, including its
  weaknesses

## Desired outcome

Competitor data becomes a first-class analytical input rather than a table nobody
reads. A conversion recommendation can cite that three nearby properties run the
target title, and the floor manager can see where the mix is behind the market —
with the confidence of that claim stated honestly.

## Acceptance criteria

1. A new deterministic module in `analytics/` computes, for each title in the
   competitor data: how many competitor properties operate it, total observed
   units, our own unit count, and a **gap score** combining competitor adoption
   with our absence.
2. Titles operated by **at least two** competitor properties that we operate
   **zero** units of are surfaced as coverage gaps, ranked by total competitor
   units.
3. For shared titles, the response reports our unit count against the mean
   competitor unit count, and flags where we are more than 40% below it.
4. Titles observed **only** under a promotional note are marked
   `promotion_influenced: true`, and this is stated wherever the title is cited
   as evidence.
5. `GET /api/market/gaps` returns the analysis, with `is_synthetic: true` and the
   standard disclaimer, matching the shape of the other market endpoints.
6. Conversion recommendations from spec 002 gain an optional
   `competitor_validation` field naming how many competitor properties operate
   the suggested title. Absent when the target appears on no competitor floor.
7. A new agent tool `find_coverage_gaps` is registered in `agent/tools.py`, so
   *"what are competitors running that we aren't?"* is answerable in chat and
   through the `slotsight` MCP server.
8. The web UI's Market view gains a **Coverage gaps** section listing the top
   gaps with competitor counts, carrying the synthetic-data marker.
9. The confidence of any gap finding degrades explicitly when it rests on fewer
   than three competitor sightings — this must be visible in the payload, not
   just implied by the number.
10. Full pipeline for a 30-day window still completes in under 2 seconds.

## Out of scope

- **Any new data source.** This spec analyses the competitor data already
  generated. Adding a real feed is a different problem with licensing attached.
- **Scraping anything.** Permanently out of scope. See [`NOTICE.md`](../../NOTICE.md).
- **Pricing, payback, or par comparisons** against competitors — we do not have
  that data and inventing it would be dishonest.
- **Geographic or drive-time weighting.** Interesting, needs data we do not have.
- Automated actions of any kind. SlotSight recommends; humans decide.

## Open questions

*(Resolve these with `/spec-clarify` before planning.)*

1. **Should a gap score be a single number or a set of dimensions?** A single
   ranked score is easier to act on and easier to mistrust. Dimensions are
   honest but harder to sort. Which failure is worse here?
2. **How should a title that only one competitor runs be treated?** Criterion 2
   sets the bar at two properties, which may be too strict in a four-property
   market — but one sighting is close to anecdote.
3. **Does competitor validation belong in the recommendation rationale prose, or
   only as structured evidence?** Prose is more persuasive, which is exactly why
   it may be the wrong place for a weak signal.
4. **Should coverage gaps appear on the Recommendations page as their own
   action type,** or stay confined to the Market view? A gap is not yet a
   recommendation — nothing says we *should* carry a title merely because
   rivals do.

## Constraints

Bound by the [Constitution](../../.specify/memory/constitution.md). The ones that
bite hardest here:

- **I — analytics stay deterministic.** The gap score is computed, not inferred.
  The chat layer gets a tool, never a prompt instruction to "consider competitors".
- **II — every finding carries evidence.** A gap claim names the properties and
  the sighting dates.
- **IV — doing nothing is valid.** If the mix is competitive, say so plainly.
- **IX — synthetic data declares itself.** Every payload and every UI surface.

## Notes for whoever plans this

The competitor data is **thin on purpose** — four fictional properties, a handful
of sightings each. That is realistic: this class of data is always sparse, and
the correct response to sparse data is to state confidence honestly rather than
to compute a more precise-looking number.

Resist the urge to make the gap score sophisticated. A weighted composite over
seven sightings is false precision, and criterion 9 exists to stop it.
