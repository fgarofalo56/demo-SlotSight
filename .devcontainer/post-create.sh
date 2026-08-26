#!/usr/bin/env bash
# Dev container setup. Runs once, after the container is created.
set -euo pipefail

echo "→ installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "→ enabling pnpm"
corepack enable && corepack prepare pnpm@latest --activate

echo "→ installing API dependencies"
cd apps/api && uv venv && uv pip install -e ".[dev]" && cd ../..

echo "→ installing web dependencies"
cd apps/web && pnpm install && cd ../..

# Git hooks are opt-in by design; the dev container opts in for you.
echo "→ wiring git hooks"
git config core.hooksPath .githooks

cat <<'BANNER'

  ┌──────────────────────────────────────────────────────────┐
  │  SlotSight — Neon Palms Casino Resort                     │
  │  All data is synthetic. See NOTICE.md.                    │
  ├──────────────────────────────────────────────────────────┤
  │  make up      start the full stack                        │
  │  make gates   lint + types + tests                        │
  │  make help    everything else                             │
  └──────────────────────────────────────────────────────────┘

BANNER
