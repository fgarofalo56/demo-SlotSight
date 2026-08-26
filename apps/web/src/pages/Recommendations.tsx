import { useState } from 'react'
import { EmptyState, ErrorState, Panel, Spinner, SyntheticBadge } from '../components/ui'
import { api } from '../lib/api'
import { actionMeta, money, priorityStyle } from '../lib/format'
import { useApi } from '../lib/useApi'
import type { RecommendationItem } from '../lib/types'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'convert', label: 'Convert' },
  { value: 'remove', label: 'Remove' },
  { value: 'investigate', label: 'Investigate' },
  { value: 'monitor', label: 'Monitor' },
  { value: 'no_action', label: 'All clear' },
]

function Card({ rec }: { rec: RecommendationItem }) {
  const [open, setOpen] = useState(false)
  const priority = priorityStyle(rec.priority)
  const action = actionMeta(rec.action)

  return (
    <article className="np-panel p-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-xl" aria-hidden="true">
            {action.icon}
          </span>
          <div>
            <h3 className="font-display text-base text-bone">{rec.headline}</h3>
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[0.68rem]">
              <span
                className={`rounded px-1.5 py-0.5 uppercase tracking-wider ${priority.bg} ${priority.text}`}
              >
                {priority.label}
              </span>
              <span className="rounded bg-bone/10 px-1.5 py-0.5 uppercase tracking-wider text-bone-dim">
                {action.label}
              </span>
              <span className="font-mono text-bone-dim">{rec.subject_id}</span>
              <span className="text-bone-dim">confidence: {rec.confidence}</span>
              {rec.uses_synthetic_market_data && <SyntheticBadge compact />}
            </div>
          </div>
        </div>

        {rec.estimated_annual_impact_dollars ? (
          <div className="text-right">
            <div className="font-display text-xl text-gold np-neon-text">
              {money(rec.estimated_annual_impact_dollars)}
            </div>
            <div className="text-[0.65rem] uppercase tracking-wider text-bone-dim">
              est. annual impact
            </div>
          </div>
        ) : null}
      </header>

      <p className="mt-3 text-sm leading-relaxed text-bone-dim">{rec.rationale}</p>

      <button
        onClick={() => setOpen((o) => !o)}
        className="mt-3 text-xs text-cyan underline-offset-2 hover:underline"
        aria-expanded={open}
      >
        {open ? 'Hide evidence' : `Show evidence (${rec.evidence.length})`}
      </button>

      {open && (
        <div className="mt-3 space-y-3 border-l-2 border-cyan/30 pl-4">
          <ul className="space-y-1.5 text-xs text-bone-dim">
            {rec.evidence.map((e, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-cyan" aria-hidden="true">
                  ›
                </span>
                <span>{e}</span>
              </li>
            ))}
          </ul>

          {rec.monitoring_instruction && (
            <div className="rounded-md bg-gold/8 p-3 text-xs text-bone-dim">
              <span className="font-medium text-gold">Measure it: </span>
              {rec.monitoring_instruction}
            </div>
          )}

          <p className="text-[0.65rem] text-bone-dim/70">
            Sources: {rec.data_sources.join(' · ')}
          </p>
        </div>
      )}
    </article>
  )
}

export function Recommendations({ windowDays }: { windowDays: number }) {
  const [filter, setFilter] = useState('')
  const recs = useApi(
    () => api.recommendations({ days: windowDays, action: filter || undefined, limit: 40 }),
    [windowDays, filter],
  )

  return (
    <div className="space-y-4">
      <Panel
        title="Recommendations"
        subtitle={
          recs.data
            ? `${recs.data.total} findings over ${recs.data.window_days} days · ranked by priority, then estimated impact`
            : 'Loading…'
        }
      >
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-md border px-3 py-1.5 text-xs transition ${
                filter === f.value
                  ? 'border-gold/60 bg-gold/20 text-gold'
                  : 'border-bone/15 bg-bone/5 text-bone-dim hover:bg-bone/10'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-bone-dim">
          Data-quality findings outrank performance findings deliberately: a conclusion drawn
          from untrustworthy numbers is worse than no conclusion. Healthy areas are reported
          explicitly, so silence is never ambiguous.
        </p>
      </Panel>

      {recs.loading && <Spinner label="Analysing the floor" />}
      {recs.error && <ErrorState error={recs.error} onRetry={recs.reload} />}
      {recs.data?.recommendations.length === 0 && (
        <EmptyState message="No findings match this filter." />
      )}

      <div className="space-y-3">
        {recs.data?.recommendations.map((r) => <Card key={r.id} rec={r} />)}
      </div>
    </div>
  )
}
