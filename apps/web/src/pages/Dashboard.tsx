import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ErrorState, KpiTile, Panel, PeerIndexChip, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { index, money, moneyCompact, percent, shortDate } from '../lib/format'
import { useApi } from '../lib/useApi'

export function Dashboard({ windowDays }: { windowDays: number }) {
  const summary = useApi(() => api.floorSummary(windowDays), [windowDays])
  const trend = useApi(() => api.trend(90), [])

  if (summary.loading) return <Spinner label="Reading the floor" />
  if (summary.error) return <ErrorState error={summary.error} onRetry={summary.reload} />
  if (!summary.data) return null

  const s = summary.data
  const chartData = (trend.data?.points ?? []).map((p) => ({
    date: shortDate(p.business_date),
    win: p.win_dollars,
    theo: p.theo_win_dollars,
  }))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Win"
          value={moneyCompact(s.win_dollars)}
          sub={`${s.window_days} days`}
          accent="gold"
        />
        <KpiTile
          label="Coin-in"
          value={moneyCompact(s.coin_in_dollars)}
          sub="total wagered"
          accent="cyan"
        />
        <KpiTile
          label="Floor WPUPD"
          value={money(s.floor_wpupd)}
          sub="per unit per day"
          change={s.wpupd_change_pct}
          accent="magenta"
        />
        <KpiTile
          label="Hold"
          value={percent(s.floor_hold_pct)}
          sub={`${s.active_machine_count} active units`}
          accent="emerald"
        />
      </div>

      <Panel
        title="Daily win"
        subtitle="Actual against theoretical. The gap is short-run variance, not performance."
      >
        {trend.loading ? (
          <Spinner label="Loading trend" />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="winFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F5C518" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#F5C518" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F5F1E8" strokeOpacity={0.08} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#A8A396', fontSize: 11 }}
                  interval="preserveStartEnd"
                  minTickGap={40}
                />
                <YAxis
                  tick={{ fill: '#A8A396', fontSize: 11 }}
                  tickFormatter={(v: number) => moneyCompact(v)}
                  width={62}
                />
                <Tooltip
                  contentStyle={{
                    background: '#062218',
                    border: '1px solid rgba(245,197,24,0.3)',
                    borderRadius: 8,
                    color: '#F5F1E8',
                  }}
                  formatter={(v: number, name) => [money(v), name === 'win' ? 'Actual' : 'Theo']}
                />
                <Area
                  type="monotone"
                  dataKey="theo"
                  stroke="#22D3EE"
                  strokeOpacity={0.55}
                  strokeDasharray="4 3"
                  fill="none"
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="win"
                  stroke="#F5C518"
                  fill="url(#winFill)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Panel>

      <Panel
        title="Zones"
        subtitle="Peer index is the actionable number. Floor index is shown to demonstrate why it isn't."
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gold/20 text-left text-[0.7rem] uppercase tracking-wider text-bone-dim">
                <th className="py-2 pr-4 font-medium">Zone</th>
                <th className="py-2 pr-4 text-right font-medium">Units</th>
                <th className="py-2 pr-4 text-right font-medium">WPUPD</th>
                <th className="py-2 pr-4 text-right font-medium">Hold</th>
                <th className="py-2 pr-4 text-right font-medium">Peer index</th>
                <th className="py-2 text-right font-medium">
                  Floor index <span className="text-magenta">*</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {s.zones.map((z) => (
                <tr key={z.zone_code} className="border-b border-bone/5 last:border-0">
                  <td className="py-2.5 pr-4">
                    <span className="font-mono text-xs text-gold">{z.zone_code}</span>
                    <span className="ml-2 text-bone">{z.zone_name}</span>
                    {z.is_high_limit && (
                      <span className="ml-2 rounded bg-gold/15 px-1.5 py-0.5 text-[0.65rem] uppercase tracking-wide text-gold">
                        High limit
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono text-bone-dim">
                    {z.machine_count}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono">{money(z.wpupd)}</td>
                  <td className="py-2.5 pr-4 text-right font-mono text-bone-dim">
                    {percent(z.hold_pct)}
                  </td>
                  <td className="py-2.5 pr-4 text-right">
                    <PeerIndexChip value={z.peer_index} />
                  </td>
                  <td className="py-2.5 text-right font-mono text-bone-dim/60">
                    {index(z.floor_index)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-bone-dim">
          <span className="text-magenta">*</span> Floor index compares every machine to one
          floor-wide average, so it mostly just sorts by denomination — note High Limit reading
          far above 1.00 on it and near par on peer index. Never rank on it.
        </p>
      </Panel>
    </div>
  )
}
