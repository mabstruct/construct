import { Link, useParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import MarkdownRenderer from '../components/MarkdownRenderer'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/digests/:id
// Spec: spec-v02-views.md §4.9
// Note: raw_path is intentionally NOT exposed to the SPA UI per data-model spec §11.7.
export default function DigestDetail() {
  const { workspace, id } = useParams()
  const { data, loading, error } = useFetch(`/data/${workspace}/digests.json`)

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />

  const digest = (data?.digests || []).find((d) => d.id === id)
  if (!digest) {
    return (
      <div className="py-8">
        <h1 className="font-display text-2xl text-white mb-2">Digest not found</h1>
        <p className="text-sm text-white/50">
          No digest with id <code className="text-cyan-300">{id}</code> in {workspace}.
        </p>
        <Link to={`/${workspace}/digests`} className="text-xs text-cyan-300 hover:text-cyan-200 mt-4 inline-block">
          ← Back to digests
        </Link>
      </div>
    )
  }

  return (
    <article className="py-8 space-y-8 max-w-3xl mx-auto">
      <header className="space-y-2 pb-4 border-b border-white/[0.04]">
        <div className="text-xs text-white/40 tabular-nums">
          {digest.date}
          {digest.domain && (
            <>
              <span className="text-white/20 mx-2">·</span>
              <span>{digest.domain}</span>
            </>
          )}
        </div>
        <h1 className="font-display text-3xl text-white leading-tight">
          {digest.theme || 'Research digest'}
        </h1>
        {digest.parse_status && (
          <p className="text-xs text-amber-400/80">
            Note: this digest was parsed in <em>{digest.parse_status}</em> mode — some sections may be missing.
          </p>
        )}
      </header>

      {/* Summary stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
        <Stat value={digest.papers_found ?? 0} label="found" />
        <Stat value={digest.papers_ingested ?? 0} label="ingested" />
        <Stat value={digest.papers_skipped ?? 0} label="skipped" />
        <Stat value={digest.seed_cards_created ?? 0} label="seed cards" />
      </section>

      {digest.summary_text && (
        <section>
          <h2 className="font-display text-base uppercase tracking-wider text-white/50 mb-3">Summary</h2>
          <div className="text-sm">
            <MarkdownRenderer>{digest.summary_text}</MarkdownRenderer>
          </div>
        </section>
      )}

      {digest.top_findings && digest.top_findings.length > 0 && (
        <section>
          <h2 className="font-display text-base uppercase tracking-wider text-white/50 mb-4">Top findings</h2>
          <ol className="space-y-5">
            {digest.top_findings.map((f) => (
              <li key={f.rank} className="flex gap-4">
                <span className="font-display text-2xl text-white/30 tabular-nums shrink-0 w-8 text-right">
                  {f.rank}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-3 mb-1 flex-wrap">
                    <h3 className="font-display text-base text-white leading-snug">
                      {f.url ? (
                        <a href={f.url} target="_blank" rel="noopener noreferrer"
                           className="hover:text-cyan-200 underline decoration-white/20 hover:decoration-cyan-200">
                          {f.title}
                        </a>
                      ) : (
                        f.title
                      )}
                    </h3>
                    {typeof f.relevance === 'number' && f.relevance > 0 && (
                      <span className="text-[10px] text-amber-300/80">
                        relevance {'★'.repeat(f.relevance)}
                      </span>
                    )}
                  </div>
                  {f.summary && (
                    <p className="text-sm text-white/70 leading-relaxed">{f.summary}</p>
                  )}
                  {f.cluster && (
                    <p className="text-[10px] text-white/30 mt-1.5 uppercase tracking-wider">
                      cluster · {f.cluster}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {digest.search_clusters && digest.search_clusters.length > 0 && (
        <section>
          <h2 className="font-display text-base uppercase tracking-wider text-white/50 mb-3">Search clusters</h2>
          <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.02]">
                <tr className="text-left text-[10px] uppercase tracking-wider text-white/40">
                  <th className="px-3 py-2 font-medium">Cluster</th>
                  <th className="px-3 py-2 font-medium tabular-nums">Queries</th>
                  <th className="px-3 py-2 font-medium tabular-nums">Results</th>
                  <th className="px-3 py-2 font-medium tabular-nums">Ingested</th>
                </tr>
              </thead>
              <tbody>
                {digest.search_clusters.map((c, i) => (
                  <tr key={c.id || i} className="border-t border-white/[0.04]">
                    <td className="px-3 py-2 text-white/85">{c.id}</td>
                    <td className="px-3 py-2 text-white/60 tabular-nums">{c.queries}</td>
                    <td className="px-3 py-2 text-white/60 tabular-nums">{c.results}</td>
                    <td className="px-3 py-2 text-white/60 tabular-nums">{c.ingested}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {digest.coverage_notes && (
        <section>
          <h2 className="font-display text-base uppercase tracking-wider text-white/50 mb-3">Coverage notes</h2>
          <div className="text-sm">
            <MarkdownRenderer>{digest.coverage_notes}</MarkdownRenderer>
          </div>
        </section>
      )}

      {digest.suggested_adjustments && (
        <section>
          <h2 className="font-display text-base uppercase tracking-wider text-white/50 mb-3">Suggested adjustments</h2>
          <div className="text-sm">
            <MarkdownRenderer>{digest.suggested_adjustments}</MarkdownRenderer>
          </div>
        </section>
      )}

      <div className="pt-4 border-t border-white/[0.04]">
        <Link to={`/${workspace}/digests`} className="text-xs text-cyan-300 hover:text-cyan-200">
          ← Back to {workspace} digests
        </Link>
      </div>
    </article>
  )
}

function Stat({ value, label }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] py-3">
      <div className="font-display text-2xl text-white tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-white/40 mt-1">{label}</div>
    </div>
  )
}
