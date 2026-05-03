import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import MetricTile from '../components/MetricTile'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/landscape
// Spec: spec-v02-views.md §4.6
export default function Landscape() {
  const { workspace } = useParams()
  const stats = useFetch(`/data/${workspace}/stats.json`)
  const domains = useFetch('/data/domains.json')

  if (stats.loading || domains.loading) return <LoadingState shape="dashboard" />
  if (stats.error) return <ErrorState message={stats.error.message} />
  if (domains.error) return <ErrorState message={domains.error.message} />

  const wsDomain = (domains.data?.domains || []).find((d) => d.id === workspace)

  if (!wsDomain) {
    return (
      <div className="py-8">
        <EmptyState
          title="This workspace doesn't have a configured domain."
          message="Run domain-init to set up its content_categories, source_priorities, and cross-domain links."
        />
      </div>
    )
  }

  const s = stats.data || {}
  const totals = s.totals || {}
  const coverage = s.category_coverage || {}
  const m = wsDomain.metrics || {}

  return (
    <div className="py-8 space-y-10">
      <DomainHeader domain={wsDomain} totals={totals} metrics={m} />

      <CategoriesSection
        workspace={workspace}
        categories={wsDomain.content_categories || []}
        coverage={coverage}
      />

      {wsDomain.cross_domain_links && wsDomain.cross_domain_links.length > 0 && (
        <CrossDomainLinks links={wsDomain.cross_domain_links} />
      )}

      <HealthRow stats={s} metrics={m} />
    </div>
  )
}

function DomainHeader({ domain, totals, metrics }) {
  const cards = totals.cards ?? metrics.cards ?? 0
  const papers = totals.papers ?? metrics.papers ?? 0
  const conf = (metrics.avg_confidence ?? 0).toFixed(2)
  return (
    <header className="pb-4 border-b border-white/[0.04]">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1 className="font-display text-3xl text-white tracking-tight">{domain.name}</h1>
        {domain.status && (
          <span className="text-[10px] uppercase tracking-wider text-cyan-300 border border-cyan-400/30 bg-cyan-400/5 rounded-full px-2 py-0.5">
            {domain.status}
          </span>
        )}
      </div>
      {domain.description && (
        <p className="text-sm text-white/50 mt-2 max-w-2xl">{domain.description}</p>
      )}
      <p className="text-xs text-white/30 mt-3 tabular-nums">
        {cards} cards · {papers} papers · conf {conf}
      </p>
    </header>
  )
}

function CategoriesSection({ workspace, categories, coverage }) {
  const cells = useMemo(() => {
    // Cells = the union of declared categories and any covered ones.
    const set = new Set([...categories, ...Object.keys(coverage)])
    const list = Array.from(set).sort()
    return list.map((cat) => ({
      name: cat,
      count: coverage[cat] || 0,
      declared: categories.includes(cat),
    }))
  }, [categories, coverage])

  if (cells.length === 0) {
    return (
      <section>
        <h2 className="font-display text-xl text-white/80 mb-4">Categories</h2>
        <p className="text-sm text-white/40">
          No content_categories declared for this domain.
        </p>
      </section>
    )
  }

  // Intensity scale relative to the busiest cell so empty domains still render legibly.
  const max = Math.max(1, ...cells.map((c) => c.count))

  return (
    <section>
      <h2 className="font-display text-xl text-white/80 mb-4">Categories</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {cells.map((c) => (
          <HeatmapCell
            key={c.name}
            cell={c}
            workspace={workspace}
            intensity={c.count / max}
          />
        ))}
      </div>
      <p className="text-[10px] text-white/30 mt-3">
        Cell intensity = card count. Faint = declared but not yet covered.
      </p>
    </section>
  )
}

function HeatmapCell({ cell, workspace, intensity }) {
  const alpha = cell.count === 0 ? 0.04 : 0.08 + intensity * 0.32
  // Cell click → Wiki filtered by this category (read-mode is the default
  // verb per spec-v02-knowledge-views-spike.md §3.5). A small secondary link
  // sends users to the Artifacts table for filter-and-narrow workflows.
  // Empty cells are non-clickable.
  const wikiTo = `/${workspace}/wiki?category=${encodeURIComponent(cell.name)}`
  const artifactsTo = `/${workspace}/artifacts?content_categories=${encodeURIComponent(cell.name)}`
  const empty = cell.count === 0
  return (
    <div
      className="group relative rounded-lg border border-white/[0.06] hover:border-cyan-400/40 transition-colors px-3 py-3"
      style={{ backgroundColor: `rgba(34, 211, 238, ${alpha})` }}
    >
      {empty ? (
        <div className="text-sm text-white/85 font-medium truncate">{cell.name}</div>
      ) : (
        <Link
          to={wikiTo}
          className="block text-sm text-white/85 font-medium truncate hover:text-white"
          title={`Read cards in ${cell.name}`}
        >
          {cell.name}
        </Link>
      )}
      <div className="flex items-baseline gap-2 mt-1">
        <span className="font-display text-xl text-white tabular-nums">{cell.count}</span>
        {empty && (
          <span className="text-[10px] text-white/40 italic">not yet covered</span>
        )}
      </div>
      {!empty && (
        <Link
          to={artifactsTo}
          className="mt-1 inline-block text-[10px] text-white/35 hover:text-cyan-200"
          title="Open filtered Artifacts table"
        >
          → Artifacts table
        </Link>
      )}
    </div>
  )
}

function CrossDomainLinks({ links }) {
  return (
    <section>
      <h2 className="font-display text-xl text-white/80 mb-4">Cross-domain links</h2>
      <ul className="space-y-1.5">
        {links.map((l) => (
          <li key={l.to} className="flex items-baseline gap-2 text-sm">
            <span className="text-white/40">→</span>
            <Link
              to={`/${l.to}/`}
              className="text-cyan-300 hover:text-cyan-200 underline underline-offset-2"
            >
              {l.to}
            </Link>
            {l.note && <span className="text-white/50">— {l.note}</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}

function HealthRow({ stats, metrics }) {
  const orphans = stats.orphan_cards ?? metrics.orphan_cards ?? 0
  const conf = stats.avg_confidence ?? metrics.avg_confidence
  const density = stats.connection_density
  return (
    <section>
      <h2 className="font-display text-xl text-white/80 mb-4">Health</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricTile value={orphans} label="orphans" sublabel="cards with no connection" />
        {conf !== undefined && (
          <MetricTile value={Number(conf).toFixed(2)} label="avg confidence" />
        )}
        {density !== undefined && (
          <MetricTile value={Number(density).toFixed(3)} label="density" sublabel="edges / max-edges" />
        )}
      </div>
    </section>
  )
}
