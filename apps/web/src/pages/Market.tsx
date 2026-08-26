import { useState } from 'react'
import { ErrorState, Panel, Spinner, SyntheticBadge } from '../components/ui'
import { api } from '../lib/api'
import { delta, index } from '../lib/format'
import { useApi } from '../lib/useApi'

export function Market() {
  const [excludeOwned, setExcludeOwned] = useState(false)
  const market = useApi(
    () => api.marketTitles({ exclude_owned: excludeOwned }),
    [excludeOwned],
  )

  return (
    <Panel
      title="Market intelligence"
      subtitle="How titles perform in comparable markets. Titles we do NOT operate are the opportunities."
      actions={<SyntheticBadge />}
    >
      <div className="mb-4 flex items-center gap-3">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-bone-dim">
          <input
            type="checkbox"
            checked={excludeOwned}
            onChange={(e) => setExcludeOwned(e.target.checked)}
            className="h-4 w-4 accent-[#F5C518]"
          />
          Opportunities only (titles we don&apos;t operate)
        </label>
      </div>

      {market.data && (
        <div className="mb-4 rounded-md border border-cyan/30 bg-cyan/5 p-3 text-xs text-bone-dim">
          <strong className="text-cyan">Provenance: </strong>
          {market.data.disclaimer}
        </div>
      )}

      {market.loading && <Spinner label="Reading the market feed" />}
      {market.error && <ErrorState error={market.error} onRetry={market.reload} />}

      {market.data && (
        <div className="max-h-[30rem] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-felt-deep/95 backdrop-blur">
              <tr className="border-b border-gold/20 text-left text-[0.7rem] uppercase tracking-wider text-bone-dim">
                <th className="py-2 pr-3 font-medium">Title</th>
                <th className="py-2 pr-3 font-medium">Segment</th>
                <th className="py-2 pr-3 text-right font-medium">Market index</th>
                <th className="py-2 pr-3 text-right font-medium">30-day trend</th>
                <th className="py-2 text-right font-medium">On our floor</th>
              </tr>
            </thead>
            <tbody>
              {market.data.titles.map((t) => (
                <tr key={`${t.provider}-${t.title}`} className="border-b border-bone/5 last:border-0">
                  <td className="py-2 pr-3">
                    <span className="text-bone">{t.title}</span>
                    <span className="ml-2 text-[0.65rem] text-bone-dim">{t.manufacturer}</span>
                  </td>
                  <td className="py-2 pr-3 text-xs text-bone-dim">{t.segment}</td>
                  <td className="py-2 pr-3 text-right">
                    <span
                      className={`font-mono ${
                        t.market_index >= 1.1
                          ? 'text-emerald-400'
                          : t.market_index < 0.92
                            ? 'text-magenta'
                            : 'text-bone-dim'
                      }`}
                    >
                      {index(t.market_index)}
                    </span>
                    <span className="ml-2 text-[0.65rem] text-bone-dim">
                      {delta(t.outperformance_pct, 0)}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-xs">
                    <span className={t.is_rising ? 'text-emerald-400' : 'text-bone-dim'}>
                      {t.is_rising ? '▲' : '·'} {delta(t.trend_30d_pct)}
                    </span>
                  </td>
                  <td className="py-2 text-right">
                    {t.on_our_floor ? (
                      <span className="rounded bg-bone/10 px-1.5 py-0.5 text-[0.65rem] text-bone-dim">
                        Operating
                      </span>
                    ) : (
                      <span className="rounded bg-gold/15 px-1.5 py-0.5 text-[0.65rem] text-gold">
                        Opportunity
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
