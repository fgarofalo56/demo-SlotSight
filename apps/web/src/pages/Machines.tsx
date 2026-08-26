import { useState } from 'react'
import { EmptyState, ErrorState, Panel, PeerIndexChip, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { money, percent } from '../lib/format'
import { useApi } from '../lib/useApi'

const ZONES = [
  { code: '', label: 'All zones' },
  { code: 'HL', label: 'High Limit' },
  { code: 'MFN', label: 'Main Floor North' },
  { code: 'MFS', label: 'Main Floor South' },
  { code: 'PROM', label: 'Promenade' },
  { code: 'BAR', label: 'Bar Tops' },
  { code: 'NSM', label: 'Non-Smoking' },
]

const DENOMS = [
  { value: '', label: 'All denominations' },
  { value: '1', label: 'Penny' },
  { value: '5', label: 'Nickel' },
  { value: '25', label: 'Quarter' },
  { value: '100', label: '$1' },
  { value: '500', label: '$5' },
  { value: '2500', label: '$25' },
]

const TYPES = [
  { value: '', label: 'All game types' },
  { value: 'video_reel', label: 'Video Reel' },
  { value: 'mechanical_reel', label: 'Mechanical Reel' },
  { value: 'video_poker', label: 'Video Poker' },
  { value: 'keno_multigame', label: 'Multigame' },
]

const selectClass =
  'rounded-md border border-gold/25 bg-felt-deep px-2.5 py-1.5 text-sm text-bone ' +
  'focus:border-gold/60 focus:outline-none'

export function Machines({ windowDays }: { windowDays: number }) {
  const [zone, setZone] = useState('')
  const [denom, setDenom] = useState('')
  const [gameType, setGameType] = useState('')
  const [descending, setDescending] = useState(false)

  const machines = useApi(
    () =>
      api.machines({
        days: windowDays,
        zone: zone || undefined,
        denomination_cents: denom ? Number(denom) : undefined,
        game_type: gameType || undefined,
        sort: 'peer_index',
        descending,
        limit: 150,
      }),
    [windowDays, zone, denom, gameType, descending],
  )

  const flags = useApi(() => api.outliers(windowDays, 50), [windowDays])
  const untrusted = new Set((flags.data?.data_quality_flags ?? []).map((f) => f.asset_number))

  return (
    <Panel
      title="Machines"
      subtitle={
        machines.data
          ? `${machines.data.total} units match · showing ${machines.data.returned} · sorted by peer index`
          : 'Loading…'
      }
      actions={
        <button
          onClick={() => setDescending((d) => !d)}
          className="rounded-md border border-gold/30 bg-gold/10 px-3 py-1.5 text-xs text-gold transition hover:bg-gold/20"
        >
          {descending ? '▲ Best first' : '▼ Worst first'}
        </button>
      }
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <select
          value={zone}
          onChange={(e) => setZone(e.target.value)}
          className={selectClass}
          aria-label="Filter by zone"
        >
          {ZONES.map((z) => (
            <option key={z.code} value={z.code}>
              {z.label}
            </option>
          ))}
        </select>
        <select
          value={denom}
          onChange={(e) => setDenom(e.target.value)}
          className={selectClass}
          aria-label="Filter by denomination"
        >
          {DENOMS.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
        <select
          value={gameType}
          onChange={(e) => setGameType(e.target.value)}
          className={selectClass}
          aria-label="Filter by game type"
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {machines.loading && <Spinner label="Querying the floor" />}
      {machines.error && <ErrorState error={machines.error} onRetry={machines.reload} />}

      {machines.data && machines.data.machines.length === 0 && (
        <EmptyState message="No machines match these filters." />
      )}

      {machines.data && machines.data.machines.length > 0 && (
        <div className="max-h-[32rem] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-felt-deep/95 backdrop-blur">
              <tr className="border-b border-gold/20 text-left text-[0.7rem] uppercase tracking-wider text-bone-dim">
                <th className="py-2 pr-3 font-medium">Asset</th>
                <th className="py-2 pr-3 font-medium">Title</th>
                <th className="py-2 pr-3 font-medium">Zone</th>
                <th className="py-2 pr-3 font-medium">Denom</th>
                <th className="py-2 pr-3 text-right font-medium">WPUPD</th>
                <th className="py-2 pr-3 text-right font-medium">Hold</th>
                <th className="py-2 text-right font-medium">Peer index</th>
              </tr>
            </thead>
            <tbody>
              {machines.data.machines.map((m) => {
                const suspect = untrusted.has(m.asset_number)
                return (
                  <tr
                    key={m.asset_number}
                    className={`border-b border-bone/5 last:border-0 ${suspect ? 'np-hatch' : ''}`}
                  >
                    <td className="py-2 pr-3 font-mono text-xs text-gold">{m.asset_number}</td>
                    <td className="py-2 pr-3">
                      {m.title}
                      <span className="ml-2 font-mono text-[0.65rem] text-bone-dim">
                        {m.bank_id}
                      </span>
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs text-bone-dim">{m.zone_code}</td>
                    <td className="py-2 pr-3 text-xs text-bone-dim">{m.denomination_label}</td>
                    <td className="py-2 pr-3 text-right font-mono">{money(m.wpupd)}</td>
                    <td className="py-2 pr-3 text-right font-mono text-bone-dim">
                      {percent(m.hold_pct)}
                    </td>
                    <td className="py-2 text-right">
                      <PeerIndexChip value={m.peer_index} untrusted={suspect} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {untrusted.size > 0 && (
        <p className="mt-3 text-xs text-bone-dim">
          <span className="text-cyan">Hatched rows</span> have metering data inconsistent with
          their paytable and are excluded from every performance ranking.
        </p>
      )}
    </Panel>
  )
}
