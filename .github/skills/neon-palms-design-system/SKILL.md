---
name: neon-palms-design-system
description: The Neon Palms visual language — colour tokens, the peer-index colour scale, accessibility rules, and number formatting. Use when building or changing anything in apps/web/.
---

# Neon Palms design system

A casino floor at night: deep felt green, neon signage, brass and gold.
Confident, not gaudy.

## Tokens

Defined in `apps/web/src/theme/tokens.css` as Tailwind v4 `@theme` variables.

| Token | Hex | Use |
|---|---|---|
| `felt` | `#0B3D2E` | Primary surface |
| `felt-deep` | `#062218` | App background |
| `felt-light` | `#12563F` | Raised panels |
| `magenta` | `#FF2E88` | Neon accent · critical |
| `cyan` | `#22D3EE` | Neon accent · info · untrusted data |
| `gold` | `#F5C518` | Brass · headings · primary action |
| `bone` | `#F5F1E8` | Body text on dark |
| `bone-dim` | `#A8A396` | Secondary text |

## The performance colour scale

**This is the important part of this file.**

Colour is assigned by **peer index**, never by raw WPUPD.

| Band | Peer index | Colour | Glyph |
|---|---|---|---|
| Strong | ≥ 1.15 | emerald | ▲ |
| Healthy | 0.95–1.15 | bone | = |
| Watch | 0.85–0.95 | amber | ▾ |
| Critical | < 0.85 | magenta | ▼ |
| **Untrusted** | any | cyan + hatch | ? |

**Never colour a machine by raw WPUPD.** A $5 machine always out-earns a penny
machine, so colouring on the raw number just renders the denomination column
again in colour and tells the viewer nothing they did not already know.

`untrusted` **overrides every performance band.** A machine with a suspect meter
has no meaningful performance band, and showing one invites acting on a number
we do not believe.

Implemented in `apps/web/src/lib/format.ts::bandFor`, with tests.

## Accessibility

Neon on dark is easy to get wrong.

- Body text clears **4.5:1** against its surface; large text and UI chrome clear
  **3:1**.
- **Never encode meaning in colour alone.** Every status colour is paired with a
  glyph, a label, or a pattern — a red cell and a green cell look identical to
  roughly one man in twelve. The hatch pattern on untrusted rows exists for this
  reason.
- Every interactive element is keyboard-reachable with a visible focus ring.
- Charts carry a text summary or accessible table alternative.
- `prefers-reduced-motion` is respected globally.

## Number formatting

| Kind | Format | Example |
|---|---|---|
| Money in tables | No cents | `$1,235` |
| Money in tiles | Compact | `$6.4M`, `$340K` |
| Money on detail | With cents | `$1,234.56` |
| Peer index | Two decimals | `1.07` |
| Percentage | One decimal | `6.4%` |
| Change | Signed | `+4.1%`, `-12.0%` |

**Always show the window.** A number without "over 30 days" is not a fact.

## Component patterns

- **`Panel`** — the felt-and-brass card. Title, optional subtitle, optional
  actions.
- **`KpiTile`** — big neon number with label, sub-label, and optional change.
- **`PeerIndexChip`** — colour + glyph + value + a screen-reader label.
- **`SyntheticBadge`** — hatched cyan chip. **Required** on any view showing
  market or competitor data. This is a product requirement, not decoration:
  a recommendation built on invented benchmarks must never look like one built
  on real market intelligence. See [`NOTICE.md`](../../../NOTICE.md).

## Charts

Recharts, with `isAnimationActive={false}` — mount animations look broken in
screenshots and add nothing to a dashboard read at a glance.

Gold (`#F5C518`) for actual values, dashed cyan (`#22D3EE`) for theoretical or
reference lines. Grid at 8% bone opacity.

## The demo banner

Every page carries a magenta banner stating the property is fictional and the
data synthetic. It is not removable. The repository is public and a screenshot
travels further than its context.
