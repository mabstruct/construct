import { Link } from 'react-router-dom'

// Per spec-v02-views.md §4.1: workspace summary panel for the Landing grid.
export default function StatusCard({ workspace }) {
  const { id, name, description, status, metrics } = workspace
  const m = metrics || {}
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="font-display text-lg text-white truncate">{name || id}</h3>
          {description && (
            <p className="text-xs text-white/50 mt-1 line-clamp-2 leading-relaxed">{description}</p>
          )}
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <Metric value={m.papers ?? 0} label="papers" />
        <Metric value={m.cards ?? 0} label="cards" />
        <Metric value={m.connections ?? 0} label="edges" />
      </div>

      {m.cards_by_lifecycle && (m.cards ?? 0) > 0 && (
        <div className="text-[10px] text-white/40 mb-4 flex items-center gap-2 flex-wrap">
          <span>seed {m.cards_by_lifecycle.seed ?? 0}</span>
          <span className="text-white/20">·</span>
          <span>growing {m.cards_by_lifecycle.growing ?? 0}</span>
          <span className="text-white/20">·</span>
          <span>mature {m.cards_by_lifecycle.mature ?? 0}</span>
          {(m.cards_by_lifecycle.archived ?? 0) > 0 && (
            <>
              <span className="text-white/20">·</span>
              <span>archived {m.cards_by_lifecycle.archived}</span>
            </>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-white/[0.04] gap-2">
        <div className="text-[10px] text-white/30 truncate">
          {m.last_research_cycle
            ? `last research ${m.last_research_cycle}`
            : 'no research yet'}
        </div>
        <div className="flex items-center gap-3 text-xs whitespace-nowrap">
          <Link to={`/${id}`} className="text-white/60 hover:text-white">Dashboard</Link>
          <Link to={`/${id}/knowledge-graph`} className="text-white/60 hover:text-white">Graph</Link>
          <Link to={`/${id}/digests`} className="text-white/60 hover:text-white">Digests</Link>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const variants = {
    active: 'border-cyan-400/40 text-cyan-300 bg-cyan-400/5',
    paused: 'border-amber-400/40 text-amber-300 bg-amber-400/5',
    archived: 'border-white/15 text-white/40 bg-white/[0.02]',
  }
  const cls = variants[status] || variants.active
  return (
    <span className={`shrink-0 text-[10px] uppercase tracking-wider rounded-full border px-2 py-0.5 ${cls}`}>
      {status || 'active'}
    </span>
  )
}

function Metric({ value, label }) {
  return (
    <div>
      <div className="font-display text-2xl text-white tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-white/40">{label}</div>
    </div>
  )
}
