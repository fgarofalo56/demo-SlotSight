---
name: Documentation style
description: How docs in this repo are written and formatted
applyTo: "**/*.md"
---

# Documentation in SlotSight

This repository **is** documentation. The app exists so the process has
something to point at. Docs are not an afterthought here; they are the product.

## Voice

Write for a competent engineer who has not seen this codebase. Assume
intelligence, not context.

- **Lead with the point.** The first sentence of a section says what the section
  is for. No throat-clearing, no "In this section we will explore…".
- **Explain the why.** Anyone can read the code to learn *what* it does. Docs
  earn their place by explaining trade-offs, alternatives rejected, and
  landmines.
- **Prose over bullets** where the ideas connect. Bullets are for genuinely
  parallel items, not for chopping an argument into fragments.
- **Be honest about limitations.** "This is a demo; use Alembic in production"
  builds more trust than silence. A doc that oversells is a doc nobody believes
  twice.

## Formatting

Use headings, tables, and code blocks generously — this is scanned before it is
read.

- **Tables** for anything with more than two parallel facts.
- **Mermaid** for diagrams. It renders natively on GitHub, versions as text, and
  diffs cleanly. Never commit a diagram as a screenshot.
- **Emoji** as section markers, sparingly and consistently — 🎰 domain,
  🔒 security, 🚀 deploy, 🧪 testing, 🤖 AI/agents, 📖 reference.
- **Callouts** via GitHub alert syntax: `> [!NOTE]`, `> [!TIP]`,
  `> [!IMPORTANT]`, `> [!WARNING]`.
- **Every code block gets a language tag** so it highlights.

## Commands must be copy-pasteable

Show the working directory when it is not the repo root. Show expected output
when the reader needs to know what success looks like.

```bash
cd apps/api
uv run pytest -m golden -v
# → 18 passed
```

Never show a command with a placeholder that looks like a real value. `<your-
resource-name>` is unambiguous; `mycompany-openai` will be pasted verbatim by
someone.

## Links

Use relative links between repo files so they work on GitHub, in an IDE, and in
a clone. Check that anchors exist before linking to them.

## Never

- **Never put a real credential, endpoint, subscription ID, or tenant ID in
  docs.** Placeholders only. A doc is as public as the repo.
- Never present synthetic data as real. Any doc showing market benchmarks says
  they are generated. See [`../../NOTICE.md`](../../NOTICE.md).
- Never claim something works that you have not run. If it is untested, say so.
