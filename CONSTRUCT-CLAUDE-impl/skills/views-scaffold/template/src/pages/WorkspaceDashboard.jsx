import { useParams } from 'react-router-dom'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { useFetch } from '../hooks/useFetch'
import MetricTile from '../components/MetricTile'
import ActivityList from '../components/ActivityList'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/
// Spec: spec-v02-views.md §4.4
export default function WorkspaceDashboard() {
  const { workspace } = useParams()
  const stats = useFetch(`/data/${workspace}/stats.json`)
  const events = useFetch(`/data/${workspace}/events.json`)
  const domains = useFetch('/data/domains.json')

  if (stats.loading) return <LoadingState shape="dashboard" />
  if (stats.error) {
    return (
      <ErrorState
        message={`Couldn't load workspace ${workspace}: ${stats.error.message}`}
      />
    )
  }

  const s = stats.data || {}
  const totals = s.totals || {}
  const lifecycle = s.by_lifecycle || {}
  const confidence = s.by_confidence || {}
  const wsDomain = (domains.data?.domains || []).find((d) => d.id === workspace)

  if ((totals.cards ?? 0) === 0) {
    return (
      <div className="py-8">
        <DashboardHeader workspace={workspace} domain={wsDomain} stats={s} />
        <EmptyState
          title="This workspace is initialised but empty."
          message={`Run a research-cycle on ${workspace} to start populating cards.`}
        />
      </div>
    )
  }

  const lifecycleData = Object.entries(lifecycle).map(([k, v]) => ({ name: k, value: v }))
  const confidenceData = Object.entries(confidence).map(([k, v]) => ({ confidence: k, count: v }))

  return (
    <div className="py-8 space-y-10">
      <DashboardHeader workspace={workspace} domain={wsDomain} stats={s} />

      {/* Metric tiles */}
      <section>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricTile value={totals.papers ?? 0} label="papers" />
          <MetricTile value={totals.cards ?? 0} label="cards" to={`/${workspace}/artifacts`} />
          <MetricTile value={totals.connections ?? 0} label="connections" to={`/${workspace}/knowledge-graph`} />
          <MetricTile value={`${maturePct(lifecycle)}%`} label="mature" />
        </div>
      </section>

      {/* Charts */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartPanel title="Lifecycle distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={lifecycleData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                {lifecycleData.map((d, i) => (
                  <Cell key={i} fill={`var(--lifecycle-${d.name})`} />
                ))}
              </Pie>
              <Tooltip {...darkTooltip} />
            </PieChart>
          </ResponsiveContainer>
          <Legend items={lifecycleData} prefix="lifecycle" />
        </ChartPanel>

        <ChartPanel title="Confidence histogram">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={confidenceData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
              <XAxis dataKey="confidence" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.1)' }} tickLine={false} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.1)' }} tickLine={false} />
              <Tooltip {...darkTooltip} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {confidenceData.map((d, i) => (
                  <Cell key={i} fill={`var(--confidence-${d.confidence})`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </section>

      {/* Health row */}
      {(s.connection_density || s.avg_confidence || s.orphan_cards) && (
        <section className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricTile value={(s.avg_confidence ?? 0).toFixed(2)} label="avg confidence" />
          <MetricTile value={(s.connection_density ?? 0).toFixed(3)} label="density" sublabel="edges / max-edges" />
          <MetricTile value={s.orphan_cards ?? 0} label="orphans" sublabel="cards with no connection" />
        </section>
      )}

      {/* Activity */}
      <section>
        <h2 className="font-display text-xl text-white/80 mb-4">Recent activity</h2>
        <ActivityList events={(events.data?.events || []).slice(0, 10)} />
      </section>
    </div>
  )
}

function DashboardHeader({ workspace, domain, stats }) {
  const totals = stats.totals || {}
  return (
    <header className="pb-4 border-b border-white/[0.04]">
      <div className="flex items-baseline gap-3">
        <h1 className="font-display text-3xl text-white tracking-tight">
          {domain?.name || workspace}
        </h1>
        {domain?.status && (
          <span className="text-[10px] uppercase tracking-wider text-cyan-300 border border-cyan-400/30 bg-cyan-400/5 rounded-full px-2 py-0.5">
            {domain.status}
          </span>
        )}
      </div>
      {domain?.description && (
        <p className="text-sm text-white/50 mt-2 max-w-2xl">{domain.description}</p>
      )}
      <p className="text-xs text-white/30 mt-3">
        {totals.cards ?? 0} cards · {totals.connections ?? 0} edges · {totals.papers ?? 0} papers · {totals.digests ?? 0} digests
      </p>
    </header>
  )
}

function ChartPanel({ title, children }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
      <h3 className="font-display text-sm uppercase tracking-wider text-white/50 mb-4">{title}</h3>
      {children}
    </div>
  )
}

function Legend({ items, prefix }) {
  return (
    <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-white/50">
      {items.map((i) => (
        <span key={i.name} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ backgroundColor: `var(--${prefix}-${i.name})` }}
          />
          {i.name} {i.value}
        </span>
      ))}
    </div>
  )
}

function maturePct(lifecycle) {
  const total = Object.values(lifecycle).reduce((a, b) => a + (b || 0), 0)
  if (total === 0) return 0
  return Math.round(((lifecycle.mature || 0) / total) * 100)
}

const darkTooltip = {
  contentStyle: {
    background: 'rgba(0,0,0,0.85)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    fontSize: 12,
    color: 'rgba(255,255,255,0.9)',
  },
  itemStyle: { color: 'rgba(255,255,255,0.85)' },
  cursor: { fill: 'rgba(255,255,255,0.04)' },
}
