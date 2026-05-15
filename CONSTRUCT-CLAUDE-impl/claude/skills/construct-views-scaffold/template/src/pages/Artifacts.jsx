import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import FilterChip from '../components/FilterChip'
import Tag from '../components/Tag'
import ConfidencePill from '../components/ConfidencePill'
import SourceTierIndicator from '../components/SourceTierIndicator'
import CardSidePanel from '../components/CardSidePanel'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/artifacts
// Spec: spec-v02-views.md §4.7
const EPISTEMIC_TYPES = [
  'finding', 'claim', 'concept', 'method', 'paper',
  'theme', 'gap', 'provocation', 'question', 'connection',
]
const LIFECYCLE_STATES = ['seed', 'growing', 'mature', 'archived']

export default function Artifacts() {
  const { workspace } = useParams()
  const [params, setParams] = useSearchParams()
  const cards = useFetch(`/data/${workspace}/cards.json`)
  const conns = useFetch(`/data/${workspace}/connections.json`)
  const [sortBy, setSortBy] = useState('created')
  const [sortDir, setSortDir] = useState('desc')

  // Filter state from URL params
  const types = params.get('type')?.split(',').filter(Boolean) || []
  const lifecycles = params.get('lifecycle')?.split(',').filter(Boolean) || []
  const categories = params.get('content_categories')?.split(',').filter(Boolean) || []
  const confMin = params.get('conf_min') ? Number(params.get('conf_min')) : undefined
  const confMax = params.get('conf_max') ? Number(params.get('conf_max')) : undefined
  const tierMin = params.get('tier_min') ? Number(params.get('tier_min')) : undefined
  const tierMax = params.get('tier_max') ? Number(params.get('tier_max')) : undefined
  const selectedCardId = params.get('card')

  const setListParam = (key, list) => {
    const next = new URLSearchParams(params)
    if (list && list.length > 0) next.set(key, list.join(','))
    else next.delete(key)
    setParams(next)
  }
  const setRangeParam = (prefix, range) => {
    const next = new URLSearchParams(params)
    ;['min', 'max'].forEach((k) => {
      const v = range && range[k]
      if (v !== undefined) next.set(`${prefix}_${k}`, String(v))
      else next.delete(`${prefix}_${k}`)
    })
    setParams(next)
  }
  const clearAllFilters = () => {
    const next = new URLSearchParams()
    if (selectedCardId) next.set('card', selectedCardId)
    setParams(next)
  }
  const setSelected = (id) => {
    const next = new URLSearchParams(params)
    if (id) next.set('card', id)
    else next.delete('card')
    setParams(next)
  }

  const categoryOptions = useMemo(() => {
    const set = new Set()
    for (const c of cards.data?.cards || []) {
      for (const cat of c.content_categories || []) set.add(cat)
    }
    return Array.from(set).sort()
  }, [cards.data])

  const filtered = useMemo(() => {
    const all = cards.data?.cards || []
    return all.filter((c) => {
      if (types.length && !types.includes(c.epistemic_type)) return false
      if (lifecycles.length && !lifecycles.includes(c.lifecycle)) return false
      if (categories.length && !(c.content_categories || []).some((cat) => categories.includes(cat))) return false
      if (confMin !== undefined && c.confidence < confMin) return false
      if (confMax !== undefined && c.confidence > confMax) return false
      if (tierMin !== undefined && c.source_tier < tierMin) return false
      if (tierMax !== undefined && c.source_tier > tierMax) return false
      return true
    })
  }, [cards.data, types.join(','), lifecycles.join(','), categories.join(','), confMin, confMax, tierMin, tierMax])

  const sorted = useMemo(() => {
    const list = [...filtered]
    list.sort((a, b) => {
      const av = a[sortBy] ?? ''
      const bv = b[sortBy] ?? ''
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv))
      return sortDir === 'asc' ? cmp : -cmp
    })
    return list
  }, [filtered, sortBy, sortDir])

  const onSort = (col) => {
    if (sortBy === col) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    else { setSortBy(col); setSortDir('desc') }
  }

  if (cards.loading) return <LoadingState shape="cards-table" />
  if (cards.error) return <ErrorState message={cards.error.message} />

  const hasFilters = types.length || lifecycles.length || categories.length ||
    confMin !== undefined || confMax !== undefined || tierMin !== undefined || tierMax !== undefined
  const allCards = cards.data?.cards || []
  const allConns = conns.data?.connections || []
  const selectedCard = allCards.find((c) => c.id === selectedCardId)

  return (
    <div className="py-6">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <h1 className="font-display text-2xl text-white">Artifacts</h1>
        <span className="text-xs text-white/40">
          {sorted.length} of {allCards.length} cards
        </span>
      </div>

      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <FilterChip
          label="Type"
          mode="multi"
          options={EPISTEMIC_TYPES}
          value={types}
          onChange={(v) => setListParam('type', v)}
        />
        <FilterChip
          label="Lifecycle"
          mode="multi"
          options={LIFECYCLE_STATES}
          value={lifecycles}
          onChange={(v) => setListParam('lifecycle', v)}
        />
        {categoryOptions.length > 0 && (
          <FilterChip
            label="Category"
            mode="multi"
            options={categoryOptions}
            value={categories}
            onChange={(v) => setListParam('content_categories', v)}
          />
        )}
        <FilterChip
          label="Confidence"
          mode="range"
          value={{ min: confMin, max: confMax }}
          onChange={(r) => setRangeParam('conf', r)}
          min={1}
          max={5}
        />
        <FilterChip
          label="Source tier"
          mode="range"
          value={{ min: tierMin, max: tierMax }}
          onChange={(r) => setRangeParam('tier', r)}
          min={1}
          max={5}
        />
        {hasFilters && (
          <button
            onClick={clearAllFilters}
            className="text-xs text-white/50 hover:text-white px-2 py-1"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Table */}
      {sorted.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No cards match the filters' : 'No cards yet'}
          message={hasFilters
            ? 'Try clearing some filters above.'
            : `Run a research-cycle on ${workspace} to create cards.`}
        />
      ) : (
        <div className="border border-white/[0.06] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.02]">
              <tr className="text-left text-[10px] uppercase tracking-wider text-white/40">
                <Th onClick={() => onSort('title')} active={sortBy === 'title'} dir={sortDir}>Title</Th>
                <Th onClick={() => onSort('epistemic_type')} active={sortBy === 'epistemic_type'} dir={sortDir}>Type</Th>
                <Th onClick={() => onSort('confidence')} active={sortBy === 'confidence'} dir={sortDir}>Conf</Th>
                <Th onClick={() => onSort('source_tier')} active={sortBy === 'source_tier'} dir={sortDir}>Tier</Th>
                <Th onClick={() => onSort('lifecycle')} active={sortBy === 'lifecycle'} dir={sortDir}>Lifecycle</Th>
                <Th>Conns</Th>
                <Th onClick={() => onSort('last_reviewed')} active={sortBy === 'last_reviewed'} dir={sortDir}>Last reviewed</Th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => setSelected(c.id)}
                  className={`border-t border-white/[0.04] cursor-pointer transition-colors ${
                    c.id === selectedCardId ? 'bg-cyan-400/5' : 'hover:bg-white/[0.03]'
                  }`}
                >
                  <td className="px-3 py-2 text-white/90 max-w-md truncate">{c.title}</td>
                  <td className="px-3 py-2"><Tag tone="type">{c.epistemic_type}</Tag></td>
                  <td className="px-3 py-2"><ConfidencePill value={c.confidence} /></td>
                  <td className="px-3 py-2"><SourceTierIndicator value={c.source_tier} /></td>
                  <td className="px-3 py-2"><Tag tone={`lifecycle_${c.lifecycle}`}>{c.lifecycle}</Tag></td>
                  <td className="px-3 py-2 text-white/60 tabular-nums">{(c.connects_to || []).length}</td>
                  <td className="px-3 py-2 text-white/40 tabular-nums text-xs">{c.last_reviewed || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedCard && (
        <CardSidePanel
          card={selectedCard}
          connections={allConns}
          workspace={workspace}
          onClose={() => setSelected(null)}
          onSelect={(id) => setSelected(id)}
        />
      )}
    </div>
  )
}

function Th({ children, onClick, active, dir }) {
  if (!onClick) return <th className="px-3 py-2 font-medium">{children}</th>
  return (
    <th className="px-3 py-2 font-medium">
      <button
        onClick={onClick}
        className={`inline-flex items-center gap-1 hover:text-white transition-colors ${active ? 'text-white' : ''}`}
      >
        {children}
        {active && <span className="text-cyan-300">{dir === 'asc' ? '↑' : '↓'}</span>}
      </button>
    </th>
  )
}
