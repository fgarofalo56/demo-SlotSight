---
name: React & TypeScript conventions
description: Frontend patterns and the Neon Palms design language
applyTo: "apps/web/**/*.{ts,tsx,css}"
---

# Frontend in SlotSight

React 19 + Vite + TypeScript (strict) + Tailwind v4 + Recharts.

## TypeScript

Strict mode. **No `any`. No non-null assertions (`!`).** If a value can be
absent, model it and handle it — an empty floor, a machine with no data in the
window, and a failed fetch are all real states this UI will hit.

Types for API payloads live in `src/lib/types.ts` and mirror the FastAPI
schemas in `apps/api/src/slotsight/schemas/`. If you change one, change both.

## Components

Function components with hooks. One component per file, named the same as the
file. Co-locate a component's small helpers; promote to `lib/` only on the
second consumer.

Keep data fetching in `src/lib/api.ts` and out of components. A component that
knows a URL is a component you cannot test.

## Neon Palms design language

Casino floor at night: deep felt green, neon signage, brass and gold accents.
Confident, not gaudy. Tokens live in `src/theme/tokens.css`.

| Token | Hex | Use |
|---|---|---|
| `--np-felt` | `#0B3D2E` | Primary surface — the felt |
| `--np-felt-deep` | `#062218` | App background |
| `--np-magenta` | `#FF2E88` | Neon accent, alerts, critical |
| `--np-cyan` | `#22D3EE` | Neon accent, info, links |
| `--np-gold` | `#F5C518` | Brass, headings, primary actions |
| `--np-bone` | `#F5F1E8` | Body text on dark |

Semantic performance colors — **always by peer index, never by raw WPUPD**:

| Meaning | Peer index | Token |
|---|---|---|
| Strong | ≥ 1.15 | `--np-good` emerald |
| Healthy | 0.95–1.15 | `--np-bone` neutral |
| Watch | 0.85–0.95 | `--np-warn` amber |
| Critical | < 0.85 | `--np-magenta` |
| Untrusted data | any | `--np-cyan` + hatch pattern |

**Never color a machine by raw WPUPD.** A $5 machine will always out-earn a
penny machine; coloring on the raw number just renders the denomination column
again in colour. See the peer-index rule in
[`../copilot-instructions.md`](../copilot-instructions.md).

## Number formatting

- Money: `$1,234` — no cents in tables, cents only on a detail view.
- Peer index: two decimals, `1.07`.
- Percentages: one decimal with the sign where it is a change, `-4.1%`.
- Always show the window. A number without "over 30 days" is not a fact.

## Accessibility

Neon on dark is easy to get wrong. Body text must clear **4.5:1** against its
surface; large text and UI chrome must clear **3:1**.

Never encode meaning in colour alone — pair every status colour with an icon,
a label, or a shape. A red cell and a green cell look identical to roughly one
man in twelve.

Every interactive element is reachable and operable by keyboard, with a visible
focus ring. Charts carry a text summary or an accessible table alternative.

## Synthetic data must look synthetic

Any view showing market benchmarks or competitor data must carry a visible
"synthetic data" marker. This is a product requirement, not decoration — see
[`../../NOTICE.md`](../../NOTICE.md). The API returns `is_synthetic` on every
market payload; surface it.
