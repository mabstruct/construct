import { Link, useParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/digests
// Spec: spec-v02-views.md §4.8
// Date-range chip filter deferred to v0.2.1 (date-picker UI not built);
// for now sorted by date DESC fixed.
export default function Digests() {
  const { workspace } = useParams()
  const { data, loading, error } = useFetch(`/data/${workspace}/digests.json`)

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />

  const digests = data?.digests || []

  return (
    <div className="py-8 space-y-6">
      <header>
        <h1 className="font-display text-3xl text-white tracking-tight">Digests</h1>
        <p className="text-sm text-white/50 mt-1">
          {digests.length} research digest{digests.length === 1 ? '' : 's'} · {workspace}
        </p>
      </header>

      {digests.length === 0 ? (
        <EmptyState
          title="No research digests yet"
          message={`Run a research-cycle on ${workspace} to produce a digest.`}
        />
      ) : (
        <ul className="divide-y divide-white/[0.04] border-y border-white/[0.04]">
          {digests.map((d) => (
            <li key={d.id}>
              <Link
                to={`/${workspace}/digests/${d.id}`}
                className="block py-4 px-2 -mx-2 hover:bg-white/[0.02] rounded transition-colors"
              >
                <div className="flex items-baseline gap-3 mb-1">
                  <span className="font-display text-sm text-white/40 tabular-nums shrink-0 w-24">
                    {d.date}
                  </span>
                  <span className="font-display text-base text-white truncate">
                    {d.theme || 'Untitled'}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-white/50 ml-[6.75rem]">
                  <span className="tabular-nums">{d.papers_ingested ?? 0} ingested</span>
                  <span className="text-white/20">·</span>
                  <span className="tabular-nums">{d.seed_cards_created ?? 0} cards</span>
                  {d.top_findings && d.top_findings[0] && (
                    <>
                      <span className="text-white/20">·</span>
                      <span className="truncate text-white/40 italic">
                        top: “{d.top_findings[0].title}”
                      </span>
                    </>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
