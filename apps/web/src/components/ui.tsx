import type { ReactNode } from 'react'
import { bandFor, delta, index } from '../lib/format'

/* ═══════════════════════════════════════════════════════════════════════════
   Shared UI primitives for the Neon Palms theme.
   ═══════════════════════════════════════════════════════════════════════ */

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = '',
}: {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`np-panel p-5 ${className}`}>
      {(title || actions) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && (
              <h2 className="font-display text-lg tracking-wide text-gold">{title}</h2>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-bone-dim">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  )
}

export function KpiTile({
  label,
  value,
  sub,
  change,
  accent = 'gold',
}: {
  label: string
  value: string
  sub?: string
  change?: number
  accent?: 'gold' | 'cyan' | 'magenta' | 'emerald'
}) {
  const accents = {
    gold: 'text-gold',
    cyan: 'text-cyan',
    magenta: 'text-magenta',
    emerald: 'text-emerald-400',
  } as const

  const rising = change !== undefined && change >= 0

  return (
    <div className="np-panel p-4">
      <div className="text-[0.7rem] uppercase tracking-[0.14em] text-bone-dim">{label}</div>
      <div className={`mt-1.5 font-display text-3xl ${accents[accent]} np-neon-text`}>
        {value}
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {sub && <span className="text-bone-dim">{sub}</span>}
        {change !== undefined && (
          <span className={rising ? 'text-emerald-400' : 'text-magenta'}>
            {rising ? '▲' : '▼'} {delta(change)}
          </span>
        )}
      </div>
    </div>
  )
}

/**
 * A peer-index chip.
 *
 * Always pairs the colour with an arrow glyph and the numeric value, so the
 * meaning survives for a reader who cannot distinguish the colours.
 */
export function PeerIndexChip({
  value,
  untrusted = false,
  showLabel = false,
}: {
  value: number
  untrusted?: boolean
  showLabel?: boolean
}) {
  const b = bandFor(value, untrusted)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-xs ${b.bg} ${b.border} ${b.text}`}
      title={
        untrusted
          ? 'Metering data is inconsistent with the paytable — excluded from rankings'
          : `Peer index ${index(value)} — ${b.label}. 1.00 is the average of comparable units.`
      }
    >
      <span aria-hidden="true">{b.icon}</span>
      <span>{untrusted ? '—' : index(value)}</span>
      {showLabel && <span className="not-sr-only">{b.label}</span>}
      <span className="sr-only">
        {untrusted ? 'Data suspect' : `Peer index ${index(value)}, ${b.label}`}
      </span>
    </span>
  )
}

/**
 * Marks generated data as generated.
 *
 * A product requirement, not decoration. A recommendation built on invented
 * benchmarks must never look like one built on real market intelligence.
 * See NOTICE.md.
 */
export function SyntheticBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className="np-hatch inline-flex items-center gap-1.5 rounded-md border border-cyan/40 bg-cyan/10 px-2 py-0.5 text-[0.68rem] uppercase tracking-wider text-cyan"
      title="Generated for demonstration. Not sourced from any real market-data provider. See NOTICE.md."
    >
      <span aria-hidden="true">⚗</span>
      {compact ? 'Synthetic' : 'Synthetic data'}
    </span>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-bone-dim">
      <span
        className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gold/30 border-t-gold"
        aria-hidden="true"
      />
      <span className="text-sm">{label}…</span>
    </div>
  )
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: Error & { status?: number; detail?: unknown }
  onRetry?: () => void
}) {
  const detail = error.detail as { message?: string } | undefined
  return (
    <div className="np-panel border-magenta/40 p-6">
      <h3 className="font-display text-lg text-magenta">Something went wrong</h3>
      <p className="mt-2 text-sm text-bone-dim">{detail?.message ?? error.message}</p>
      {error.status === 503 && (
        <p className="mt-2 text-xs text-bone-dim">
          The analytics endpoints are unaffected — only the conversational feature needs
          Azure OpenAI.
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-md border border-gold/40 bg-gold/10 px-3 py-1.5 text-sm text-gold transition hover:bg-gold/20"
        >
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-10 text-center text-sm text-bone-dim">{message}</p>
}
