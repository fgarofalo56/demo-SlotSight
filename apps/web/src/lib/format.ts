/**
 * Formatting and the peer-index colour scale.
 *
 * The colour scale is the important part of this file. **Performance is
 * coloured by peer index, never by raw WPUPD.** A $5 machine will always
 * out-earn a penny machine; colouring on the raw number just re-renders the
 * denomination column in colour and tells you nothing.
 */

export type PerfBand = 'strong' | 'healthy' | 'watch' | 'critical' | 'untrusted'

export interface BandStyle {
  band: PerfBand
  label: string
  /** Tailwind text colour class. */
  text: string
  /** Tailwind background class for chips and cells. */
  bg: string
  border: string
  /** Paired with colour so meaning survives without colour vision. */
  icon: string
}

const BANDS: Record<PerfBand, BandStyle> = {
  strong: {
    band: 'strong',
    label: 'Strong',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    border: 'border-emerald-500/40',
    icon: '▲',
  },
  healthy: {
    band: 'healthy',
    label: 'Healthy',
    text: 'text-bone-dim',
    bg: 'bg-bone/10',
    border: 'border-bone/25',
    icon: '=',
  },
  watch: {
    band: 'watch',
    label: 'Watch',
    text: 'text-amber-400',
    bg: 'bg-amber-500/15',
    border: 'border-amber-500/40',
    icon: '▾',
  },
  critical: {
    band: 'critical',
    label: 'Critical',
    text: 'text-magenta',
    bg: 'bg-magenta/15',
    border: 'border-magenta/45',
    icon: '▼',
  },
  untrusted: {
    band: 'untrusted',
    label: 'Data suspect',
    text: 'text-cyan',
    bg: 'bg-cyan/15',
    border: 'border-cyan/45',
    icon: '?',
  },
}

/**
 * Band a machine by peer index.
 *
 * `untrusted` wins over everything: a machine whose meter is suspect has no
 * meaningful performance band, and showing one would invite acting on it.
 */
export function bandFor(peerIndex: number, untrusted = false): BandStyle {
  if (untrusted) return BANDS.untrusted
  if (peerIndex >= 1.15) return BANDS.strong
  if (peerIndex >= 0.95) return BANDS.healthy
  if (peerIndex >= 0.85) return BANDS.watch
  return BANDS.critical
}

export function money(value: number, withCents = false): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: withCents ? 2 : 0,
    maximumFractionDigits: withCents ? 2 : 0,
  }).format(value)
}

/** Compact money for tiles: $1.2M, $340K. */
export function moneyCompact(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function index(value: number): string {
  return value.toFixed(2)
}

export function percent(fraction: number, digits = 2): string {
  return `${(fraction * 100).toFixed(digits)}%`
}

/** Signed percentage for changes: +4.1%, -12.0%. */
export function delta(value: number, digits = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`
}

export function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export interface PriorityStyle {
  text: string
  bg: string
  label: string
}

const PRIORITY_STYLES: Record<string, PriorityStyle> = {
  critical: { text: 'text-magenta', bg: 'bg-magenta/20', label: 'Critical' },
  high: { text: 'text-amber-400', bg: 'bg-amber-500/20', label: 'High' },
  medium: { text: 'text-cyan', bg: 'bg-cyan/20', label: 'Medium' },
  low: { text: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Low' },
}

const UNKNOWN_PRIORITY: PriorityStyle = {
  text: 'text-bone-dim',
  bg: 'bg-bone/10',
  label: 'Unranked',
}

/**
 * Look up a priority style, always returning something renderable.
 *
 * The API's priority values are a closed set today, but a new one added
 * server-side must not blank out a card in the UI — a recommendation that
 * renders as an empty chip is worse than one labelled "Unranked".
 */
export function priorityStyle(priority: string): PriorityStyle {
  return PRIORITY_STYLES[priority] ?? UNKNOWN_PRIORITY
}

export interface ActionMeta {
  icon: string
  label: string
}

const ACTION_METAS: Record<string, ActionMeta> = {
  convert: { icon: '🔄', label: 'Convert' },
  remove: { icon: '🗑️', label: 'Remove' },
  monitor: { icon: '👁️', label: 'Monitor' },
  investigate: { icon: '🔧', label: 'Investigate' },
  no_action: { icon: '✅', label: 'No action' },
}

export function actionMeta(action: string): ActionMeta {
  return ACTION_METAS[action] ?? { icon: '•', label: action }
}
