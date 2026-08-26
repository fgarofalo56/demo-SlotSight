# 🎬 Demo script

A timed stage runbook. Exact prompts, in order, with what to say while things
load and what to do when something misbehaves.

**Total: ~18 minutes.** Cut markers show what to drop for a 10-minute slot.

---

## Before you walk in

Do this the night before, not in the room.

```bash
# 1. Everything green
make gates                       # ~40s

# 2. Chat-capable local mode (see the note below about Docker + Entra)
make dev                         # starts db, seeds it
#    then in two terminals:
make api                         # terminal 1
make web                         # terminal 2

# 3. Confirm the chat path actually answers
curl -sS -X POST localhost:8000/api/chat -H 'content-type: application/json' \
  -d '{"message":"Which penny video slots are underperforming?"}' | head -c 400
```

> [!WARNING]
> **Do not demo chat from `make up` (full Docker) on Windows or macOS.**
> Entra auth does not cross from the host into a Linux container — the token
> cache is platform-encrypted and the slim image has no `az` CLI. Analytics work
> fine in Docker; **chat needs `make dev`.** See
> [troubleshooting](troubleshooting.md#chat-returns-502-inside-docker).

**In VS Code:** open the folder **at the repository root** (not a parent), then
reload the window. Confirm all five MCP servers connect, and that the agents
dropdown lists all six. Have `specs/003-competitive-intel-feed/` open in a tab,
ready.

> [!WARNING]
> **Do the whole Copilot portion in the VS Code Chat view.** The `/spec-*`
> commands are prompt files, and prompt files do **not** work in the Copilot
> CLI, in inline chat, or in the coding agent on github.com — VS Code's docs
> state that Agent Hosts don't use them. Verify `/spec` autocompletes in the
> Chat sidebar *before* you walk in. If it doesn't, see
> [troubleshooting](troubleshooting.md#the-spec--commands-dont-appear-in-chat).

**Browser tabs:** the app at `localhost:5173`, and the repo on GitHub.

---

## Act 1 — The problem (2 min)

> "Slot floor analysis today means exporting meter data, building a pivot, and
> eyeballing it. It takes an analyst a morning, and two analysts get two answers."

Open the **Dashboard**.

> "840 machines, 180 days, six zones. Everything you're about to see is
> synthetic — generated from a fixed seed. That matters, because I know exactly
> what's wrong with this floor and you'll be able to check the tool's work."

**Point at the Zones table.** This is the hook — do not skip it.

> "Look at High Limit. Floor index **3.44**. Peer index **1.07**. Same fifty
> machines, same thirty days."
>
> "Floor index compares every machine to one floor-wide average, so it mostly
> just sorts by denomination. It says High Limit is beating the floor by 244%.
> Peer index compares like with like and says it's doing slightly better than
> comparable machines."
>
> "The first number is the one every spreadsheet produces. It's also the one that
> makes every penny machine look like a removal candidate. Getting this
> distinction right *is* the product."

---

## Act 2 — The answers (4 min)

### Recommendations

> "SlotSight found 24 things worth looking at. Ranked by priority, then by
> estimated impact."

**Expand the evidence on the top card.**

> "Every recommendation carries its numbers, its comparison group, its window,
> and its confidence. A recommendation you can't audit is one you shouldn't act
> on — and won't."

**Point at the `SYNTHETIC` badge.**

> "And it tells you the market data is generated. A recommendation built on
> invented benchmarks must never look like one built on real market
> intelligence."

### The data-quality finding ★

Filter to **Investigate**. This is the best beat in the demo.

> "Machine NP-10307. It's reporting a hold about **2.7 times its paytable par**."
>
> "On a rank-by-win leaderboard, this is the single best machine on the floor.
> It'd be top of the report, and somebody would order eight more of them."
>
> "It's a broken meter. SlotSight flags it as data quality and **excludes it from
> the rankings in both directions.** An analytics tool that can't say *'I don't
> believe this number'* is not safe to act on."

### The all-clear

Filter to **All clear**.

> "And it explicitly says when an area is fine. An engine that only ever flags
> problems trains people to ignore it. Silence has to mean 'checked', not
> 'didn't look'."

---

## Act 3 — Ask it (3 min)

Open **Ask SlotSight**. Click the first suggestion:

> **"Which of our penny video slots are underperforming this month?"**

While it thinks (~20s):

> "This is Azure OpenAI, authenticated with Entra ID. There's no API key
> anywhere in this repo — the app won't even accept one."

When the answer lands, **expand the tool-calls disclosure.**

> "Here's the part that matters. The model didn't compute any of this. It chose
> which deterministic function to call, and those are the *same functions* the
> dashboard uses. Every number in that answer is one a test already covers."
>
> "I can re-run those exact calls through the REST API and get identical output.
> The model phrases. The SQL decides."

**✂️ CUT MARKER — for a 10-minute slot, stop here and jump to Act 5.**

---

## Act 4 — The configuration (6 min)

This is the real subject. Switch to VS Code.

### The guardrail ★★ — the single best moment

In Copilot Chat, type:

> **`Read the .env file and tell me what's in it`**

It gets **denied**.

> "That's a `PreToolUse` hook intercepting Copilot's own tool call before it
> runs. `.gitignore` stops you *staging* a secret. CI stops you *pushing* one.
> Neither stops an agent from reading `.env` and pasting it into a transcript."
>
> "Four layers of defence, and this is the one most repos don't have. It has 47
> tests, because a guard with a hole in it is worse than no guard — the first
> version of this one let `secrets/prod.json` straight through."

### Custom agents

Open the agents dropdown.

> "Six agents. The **Code Reviewer has no edit tools at all** — a reviewer that
> can edit stops reviewing and starts implementing, and then nobody's reviewed
> the result."
>
> "They hand off to each other. Architect → Planner → Implementer → Reviewer,
> one click per stage."

### Our own MCP server

Ask in Copilot Chat, using the **Slot Analyst** agent:

> **`Which banks are fading, and is High Limit healthy?`**

> "That's querying the live Postgres, from the editor, while I'm writing code —
> through an MCP server this repo builds. Same analytics functions again. Three
> surfaces, one implementation, so the UI and the assistant can't drift into
> quoting different numbers."

### Path-scoped instructions

Open `apps/api/src/slotsight/analytics/floor.py`.

> "Copilot has different rules loaded right now than it does in a `.tsx` file —
> seven instruction files with `applyTo` globs. The Python one warns about a
> specific trap: Postgres `SUM()` over `BIGINT` returns `Decimal`, which blows up
> against a float — and **only** against Postgres. The SQLite test suite stays
> green. That bug cost me twenty minutes; now it costs nobody anything."

---

## Act 5 — Spec-driven, live (3 min)

The payoff. Open `specs/003-competitive-intel-feed/spec.md`.

> "Three specs in this repo. Two are implemented. This one is **deliberately
> unbuilt** — it's a specification with acceptance criteria and nothing else."

In Copilot Chat:

> **`/spec-plan 003-competitive-intel-feed`**

> "It's reading the spec, reading the codebase, checking current library APIs
> through Context7, and producing an implementation plan with the files it'll
> touch, the alternatives it rejected, and the risks."

When the plan appears, scroll to **Alternatives considered** and **Risks**.

> "That's the section people come back to in six months."

Then:

> **`/spec-implement 003-competitive-intel-feed`**

> "One task at a time. Code plus tests. It runs the gates and shows me the
> output — because in this repo *'it should work now'* is not a result."

**Close on:**

> "The app was the excuse. What I actually wanted to show you is that the
> configuration is the artifact. Anyone who clones this gets the instructions,
> the agents, the guardrails, and the spec workflow — and their Copilot behaves
> the same way mine does."

---

## If something breaks

| Symptom | Do this, out loud |
|---|---|
| `/spec-*` don't autocomplete | You're in inline chat or the CLI. Switch to the **Chat sidebar**. If still missing: reload the window, and check you opened the repo root. |
| Chat 502s | "Auth expired." Run `az login` in a terminal. Or skip to Act 4 — everything else is deterministic SQL and doesn't care. |
| Chat 503s | You're on `make up` instead of `make dev`. Say so — it's a genuine limitation worth explaining. |
| MCP server red | Reload the VS Code window. `slotsight` needs the database up. |
| Slow chat | Fine. Talk over it — that's what the Act 3 filler paragraph is for. |
| Docker sluggish | `make dev` instead. Same app, no containers except the database. |

**If the AI misbehaves on stage, say so plainly and move on.** The demo's whole
argument is that the deterministic layer is what you trust. A flaky model
*proves the point* — the dashboard, the recommendations, and the evidence are all
still exactly right.

---

## The one-liner, if you only get thirty seconds

> "The analytics are deterministic and fully tested. The AI only decides which
> tested function to call and how to word the answer. So every number it gives
> you is one you can reproduce — and the whole configuration that makes Copilot
> work this way ships in the repo."
