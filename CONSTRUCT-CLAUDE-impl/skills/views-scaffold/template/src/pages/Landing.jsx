import { Link } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import StatusCard from '../components/StatusCard'
import ArticleCard from '../components/ArticleCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /
// Spec: spec-v02-views.md §4.1
export default function Landing() {
  const { data: domains, loading: dLoading, error: dError } = useFetch('/data/domains.json')
  const { data: stats } = useFetch('/data/stats.json')
  const { data: articles } = useFetch('/data/articles.json')

  if (dLoading) return <LoadingState shape="dashboard" />
  if (dError) return (
    <ErrorState
      message={`Couldn't load workspaces: ${dError.message}. Check that views/build/data/domains.json exists.`}
    />
  )

  const workspaces = domains?.domains || []
  const totals = stats?.totals || {}
  const recent = (articles?.articles || []).slice(0, 3)

  return (
    <div className="py-8 space-y-12">
      {/* Hero band */}
      <header className="pb-6 border-b border-white/[0.04]">
        <div className="font-display text-3xl md:text-4xl text-white tracking-tight mb-2">
          CONSTRUCT
        </div>
        <p className="text-sm text-white/50">
          {totals.workspaces ?? workspaces.length} workspace{(totals.workspaces ?? workspaces.length) === 1 ? '' : 's'}
          {' · '}
          {totals.cards ?? 0} cards
          {' · '}
          {totals.connections ?? 0} connections
          {totals.articles > 0 && (
            <>
              {' · '}
              {totals.articles} articles
            </>
          )}
        </p>
      </header>

      {/* Workspace grid */}
      <section>
        <h2 className="font-display text-xl text-white/80 mb-4">Workspaces</h2>
        {workspaces.length === 0 ? (
          <EmptyState
            title="No workspaces yet"
            message="Initialise one from your CONSTRUCT conversation. Try: “Initialize cosmology”."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workspaces.map((w) => (
              <StatusCard key={w.id} workspace={w} />
            ))}
          </div>
        )}
      </section>

      {/* Cross-workspace articles strip */}
      {recent.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl text-white/80">Recent articles</h2>
            <Link
              to="/articles"
              className="text-xs text-white/50 hover:text-white transition-colors"
            >
              See all →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recent.map((a) => (
              <ArticleCard key={a.id} article={a} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
