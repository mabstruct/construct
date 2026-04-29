import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import ArticleCard from '../components/ArticleCard'
import FilterChip from '../components/FilterChip'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /articles
// Spec: spec-v02-views.md §4.2
export default function Articles() {
  const [params, setParams] = useSearchParams()
  const { data, loading, error } = useFetch('/data/articles.json')

  const types = params.get('type')?.split(',').filter(Boolean) || []
  const statuses = params.get('status')?.split(',').filter(Boolean) || []
  const workspaces = params.get('workspace')?.split(',').filter(Boolean) || []

  const setListParam = (key, list) => {
    const next = new URLSearchParams(params)
    if (list && list.length > 0) next.set(key, list.join(','))
    else next.delete(key)
    setParams(next)
  }

  const all = data?.articles || []

  const { typeOptions, statusOptions, workspaceOptions } = useMemo(() => ({
    typeOptions: [...new Set(all.map((a) => a.type).filter(Boolean))].sort(),
    statusOptions: [...new Set(all.map((a) => a.status).filter(Boolean))].sort(),
    workspaceOptions: [...new Set(all.flatMap((a) => a.workspaces || []))].sort(),
  }), [all])

  const filtered = useMemo(() => all.filter((a) => {
    if (types.length && !types.includes(a.type)) return false
    if (statuses.length && !statuses.includes(a.status)) return false
    if (workspaces.length && !(a.workspaces || []).some((w) => workspaces.includes(w))) return false
    return true
  }), [all, types.join(','), statuses.join(','), workspaces.join(',')])

  if (loading) return <LoadingState shape="dashboard" />
  if (error) return <ErrorState message={error.message} />

  const hasFilters = types.length || statuses.length || workspaces.length

  return (
    <div className="py-8 space-y-6">
      <header>
        <h1 className="font-display text-3xl text-white tracking-tight">Articles</h1>
        <p className="text-sm text-white/50 mt-1">
          {filtered.length} of {all.length} cross-workspace published outputs
        </p>
      </header>

      <div className="flex items-center gap-2 flex-wrap">
        {typeOptions.length > 0 && (
          <FilterChip label="Type" mode="multi" options={typeOptions}
            value={types} onChange={(v) => setListParam('type', v)} />
        )}
        {statusOptions.length > 0 && (
          <FilterChip label="Status" mode="multi" options={statusOptions}
            value={statuses} onChange={(v) => setListParam('status', v)} />
        )}
        {workspaceOptions.length > 0 && (
          <FilterChip label="Workspace" mode="multi" options={workspaceOptions}
            value={workspaces} onChange={(v) => setListParam('workspace', v)} />
        )}
        {hasFilters && (
          <button
            onClick={() => setParams(new URLSearchParams())}
            className="text-xs text-white/50 hover:text-white px-2 py-1"
          >
            Clear all
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No articles match the filters' : 'No articles published yet'}
          message={hasFilters
            ? 'Try clearing some filters above.'
            : 'Run synthesis on a workspace to draft an article from your knowledge cards.'}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((a) => <ArticleCard key={a.id} article={a} />)}
        </div>
      )}
    </div>
  )
}
