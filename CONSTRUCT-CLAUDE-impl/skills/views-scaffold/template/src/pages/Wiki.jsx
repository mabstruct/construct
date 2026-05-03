import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ChevronRight, Network, Search } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import FilterChip from '../components/FilterChip'
import Tag from '../components/Tag'
import ConfidencePill from '../components/ConfidencePill'
import SourceTierIndicator from '../components/SourceTierIndicator'
import MarkdownRenderer from '../components/MarkdownRenderer'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import { linkifyCardIds } from '../lib/linkifyCardIds'

// Route: /:workspace/wiki
// Spec: spec-v02-knowledge-views-spike.md §3 (Spike B / Slice 12.1, locked
// 2026-05-02). Long-scroll reading view (Option A — D4) with inline
// collapsibles. Per-card render order per §3.3:
//   anchor h2 → meta row → body → sources → out-conns → backlinks →
//   "Mentioned in" (digests + articles)
// Search/filters/URL state per §3.4. Cross-link wiring per §3.5.

const EPISTEMIC_TYPES = [
  'finding', 'claim', 'concept', 'method', 'paper',
  'theme', 'gap', 'provocation', 'question', 'connection',
]
const LIFECYCLE_STATES = ['seed', 'growing', 'mature', 'archived']

const SORT_OPTIONS = [
  { id: 'default',       label: 'Type → Category → Title' },
  { id: 'created',       label: 'Created (newest first)' },
  { id: 'last_reviewed', label: 'Last reviewed (newest first)' },
  { id: 'confidence',    label: 'Confidence (high first)' },
]

export default function Wiki() {
  const { workspace } = useParams()
  const [params, setParams] = useSearchParams()
  const cards = useFetch(`/data/${workspace}/cards.json`)
  const conns = useFetch(`/data/${workspace}/connections.json`)
  const digests = useFetch(`/data/${workspace}/digests.json`)
  const articles = useFetch(`/data/articles.json`)

  // URL-backed filter state (matches Artifacts conventions where applicable)
  const types = params.get('type')?.split(',').filter(Boolean) || []
  const lifecycles = params.get('lifecycle')?.split(',').filter(Boolean) || []
  const categories = params.get('category')?.split(',').filter(Boolean) || []
  const confMin = params.get('conf_min') ? Number(params.get('conf_min')) : undefined
  const confMax = params.get('conf_max') ? Number(params.get('conf_max')) : undefined
  const search = params.get('q') || ''
  const sortMode = params.get('sort') || 'default'
  const expandedFromUrl = useMemo(
    () => new Set((params.get('expanded') || '').split(',').filter(Boolean)),
    [params],
  )

  // Search input is debounced into the URL ?q= so typing isn't laggy and
  // doesn't pollute the back-button history (replace, not push).
  const [searchInput, setSearchInput] = useState(search)
  useEffect(() => {
    const h = setTimeout(() => {
      const next = new URLSearchParams(params)
      if (searchInput) next.set('q', searchInput)
      else next.delete('q')
      setParams(next, { replace: true })
    }, 200)
    return () => clearTimeout(h)
  }, [searchInput])

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
  const setSort = (id) => {
    const next = new URLSearchParams(params)
    if (id && id !== 'default') next.set('sort', id)
    else next.delete('sort')
    setParams(next)
  }
  const clearAllFilters = () => {
    const next = new URLSearchParams()
    if (sortMode !== 'default') next.set('sort', sortMode)
    setParams(next)
    setSearchInput('')
  }
  const toggleExpanded = (id) => {
    const set = new Set(expandedFromUrl)
    if (set.has(id)) set.delete(id)
    else set.add(id)
    const next = new URLSearchParams(params)
    if (set.size > 0) next.set('expanded', Array.from(set).join(','))
    else next.delete('expanded')
    setParams(next, { replace: true })
  }
  const expandAll = (ids) => {
    const next = new URLSearchParams(params)
    if (ids.length > 0) next.set('expanded', ids.join(','))
    else next.delete('expanded')
    setParams(next, { replace: true })
  }
  const collapseAll = () => {
    const next = new URLSearchParams(params)
    next.delete('expanded')
    setParams(next, { replace: true })
  }

  const allCards = cards.data?.cards || []
  const allConns = conns.data?.connections || []
  const allDigests = digests.data?.digests || []
  const allArticles = articles.data?.articles || []

  const cardsById = useMemo(() => {
    const m = new Map()
    for (const c of allCards) m.set(c.id, c)
    return m
  }, [allCards])

  const categoryOptions = useMemo(() => {
    const set = new Set()
    for (const c of allCards) for (const cat of c.content_categories || []) set.add(cat)
    return Array.from(set).sort()
  }, [allCards])

  // Per-card connection groupings, computed once.
  const outboundByCard = useMemo(() => {
    const m = new Map()
    for (const c of allConns) {
      if (!m.has(c.source)) m.set(c.source, [])
      m.get(c.source).push(c)
    }
    return m
  }, [allConns])
  const inboundByCard = useMemo(() => {
    const m = new Map()
    for (const c of allConns) {
      if (!m.has(c.target)) m.set(c.target, [])
      m.get(c.target).push(c)
    }
    return m
  }, [allConns])

  // "Mentioned in" derivation — scan digests' top_findings[].summary +
  // articles' body_markdown + source_cards for backticked card-ids.
  // Per spec §3.3 (item 7). Computed once per dataset.
  const mentionsByCard = useMemo(() => {
    const m = new Map()
    const ensure = (id) => {
      if (!m.has(id)) m.set(id, { digests: [], articles: [] })
      return m.get(id)
    }
    const known = new Set(allCards.map((c) => c.id))
    const extractIds = (text) => {
      if (!text) return []
      const out = []
      for (const match of text.matchAll(/`([a-z0-9][a-z0-9\-]*)`/g)) {
        if (known.has(match[1])) out.push(match[1])
      }
      return out
    }

    for (const d of allDigests) {
      const haystack = (d.top_findings || []).map((f) => `${f.title || ''} ${f.summary || ''}`).join(' ')
      const ids = new Set(extractIds(haystack))
      ids.forEach((id) => {
        const slot = ensure(id)
        if (!slot.digests.some((x) => x.id === d.id)) {
          slot.digests.push({ id: d.id, title: d.theme || d.id, date: d.date })
        }
      })
    }

    for (const a of allArticles) {
      const inThisWorkspace = !a.workspaces || a.workspaces.includes(workspace)
      if (!inThisWorkspace) continue
      const ids = new Set([
        ...extractIds(a.body_markdown || ''),
        ...((a.source_cards || []).map((s) => s?.id).filter(Boolean)),
      ])
      ids.forEach((id) => {
        const slot = ensure(id)
        if (!slot.articles.some((x) => x.id === a.id)) {
          slot.articles.push({ id: a.id, title: a.title })
        }
      })
    }

    return m
  }, [allDigests, allArticles, allCards, workspace])

  // Filter pass
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return allCards.filter((c) => {
      if (types.length && !types.includes(c.epistemic_type)) return false
      if (lifecycles.length && !lifecycles.includes(c.lifecycle)) return false
      if (categories.length && !(c.content_categories || []).some((cat) => categories.includes(cat))) return false
      if (confMin !== undefined && c.confidence < confMin) return false
      if (confMax !== undefined && c.confidence > confMax) return false
      if (needle) {
        const hay = [
          c.title || '',
          c.body_markdown || '',
          c.summary_excerpt || '',
          (c.tags || []).join(' '),
          (c.content_categories || []).join(' '),
        ].join(' ').toLowerCase()
        if (!hay.includes(needle)) return false
      }
      return true
    })
  }, [allCards, types.join(','), lifecycles.join(','), categories.join(','), confMin, confMax, search])

  const sorted = useMemo(() => {
    const list = [...filtered]
    if (sortMode === 'default') {
      list.sort((a, b) => {
        const t = (a.epistemic_type || '').localeCompare(b.epistemic_type || '')
        if (t) return t
        const ca = (a.content_categories?.[0] || '')
        const cb = (b.content_categories?.[0] || '')
        const cc = ca.localeCompare(cb)
        if (cc) return cc
        return (a.title || '').localeCompare(b.title || '')
      })
    } else if (sortMode === 'created') {
      list.sort((a, b) => (b.created || '').localeCompare(a.created || ''))
    } else if (sortMode === 'last_reviewed') {
      list.sort((a, b) => (b.last_reviewed || '').localeCompare(a.last_reviewed || ''))
    } else if (sortMode === 'confidence') {
      list.sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    }
    return list
  }, [filtered, sortMode])

  // Auto-scroll to anchor on mount + on hash change. Wait for cards to render
  // before scrolling; the deep-link target may live mid-list.
  // Auto-expand the targeted card if it isn't already expanded.
  const lastScrolledHash = useRef('')
  useEffect(() => {
    if (cards.loading) return
    const onHash = () => {
      const id = decodeURIComponent(window.location.hash.replace(/^#/, ''))
      if (!id || id === lastScrolledHash.current) return
      const el = document.getElementById(id)
      if (!el) return
      lastScrolledHash.current = id
      // Expand the targeted card so the body is visible after the jump.
      if (cardsById.has(id) && !expandedFromUrl.has(id)) {
        toggleExpanded(id)
      }
      requestAnimationFrame(() => el.scrollIntoView({ block: 'start', behavior: 'smooth' }))
    }
    onHash()
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [cards.loading, cardsById, expandedFromUrl])

  if (cards.loading) return <LoadingState />
  if (cards.error) return <ErrorState message={cards.error.message} />

  const hasFilters =
    types.length || lifecycles.length || categories.length ||
    confMin !== undefined || confMax !== undefined || search

  return (
    <div className="py-6 max-w-4xl mx-auto">
      {/* Header */}
      <header className="mb-4">
        <h1 className="font-display text-2xl text-white">Wiki</h1>
        <p className="text-xs text-white/50 mt-1">
          {sorted.length} of {allCards.length} cards · {workspace}
        </p>
      </header>

      {/* Search */}
      <div className="relative mb-3">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search title, body, tags…"
          className="w-full pl-9 pr-3 py-2 text-sm bg-white/[0.04] border border-white/10 rounded-lg text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-cyan-400/40 focus:border-cyan-400/40"
        />
      </div>

      {/* Filter toolbar */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
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
            onChange={(v) => setListParam('category', v)}
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
        {hasFilters ? (
          <button
            onClick={clearAllFilters}
            className="text-xs text-white/50 hover:text-white px-2 py-1"
          >
            Clear all
          </button>
        ) : null}

        <span className="mx-2 h-4 w-px bg-white/[0.08]" aria-hidden />

        {/* Sort dropdown */}
        <select
          value={sortMode}
          onChange={(e) => setSort(e.target.value)}
          className="text-xs bg-white/[0.04] border border-white/10 rounded-full px-3 py-1 text-white/80 hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
          aria-label="Sort"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.id} value={o.id} className="bg-black">{o.label}</option>
          ))}
        </select>

        <span className="mx-2 h-4 w-px bg-white/[0.08]" aria-hidden />

        {/* Expand/collapse all */}
        <button
          onClick={() => expandAll(sorted.map((c) => c.id))}
          className="text-xs text-white/50 hover:text-white px-2 py-1"
        >
          Expand all
        </button>
        <button
          onClick={collapseAll}
          className="text-xs text-white/50 hover:text-white px-2 py-1"
        >
          Collapse all
        </button>
      </div>

      {/* List */}
      {sorted.length === 0 ? (
        <EmptyState
          title={hasFilters ? 'No cards match the filters' : 'No cards yet'}
          message={hasFilters
            ? 'Try clearing some filters above.'
            : `Run a research-cycle on ${workspace} to create cards.`}
        />
      ) : (
        <div className="space-y-2">
          {sorted.map((c) => (
            <WikiCard
              key={c.id}
              card={c}
              cardsById={cardsById}
              outbound={outboundByCard.get(c.id) || []}
              inbound={inboundByCard.get(c.id) || []}
              mentions={mentionsByCard.get(c.id) || { digests: [], articles: [] }}
              workspace={workspace}
              expanded={expandedFromUrl.has(c.id)}
              onToggle={() => toggleExpanded(c.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function WikiCard({ card, cardsById, outbound, inbound, mentions, workspace, expanded, onToggle }) {
  const summary = card.summary_excerpt
  return (
    <article
      id={card.id}
      className="group border border-white/[0.06] rounded-xl bg-white/[0.02] scroll-mt-32 transition-colors hover:border-white/[0.12]"
    >
      <header
        className="px-5 py-3.5 cursor-pointer select-none"
        onClick={onToggle}
        role="button"
        aria-expanded={expanded}
      >
        <div className="flex items-start gap-3">
          <ChevronRight
            className={`h-4 w-4 mt-1 text-white/40 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
          />
          <div className="flex-1 min-w-0">
            <h2 className="font-display text-base md:text-lg text-white leading-snug">
              {card.title}
            </h2>
            <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
              <Tag tone="type">{card.epistemic_type}</Tag>
              <Tag tone={`lifecycle_${card.lifecycle}`}>{card.lifecycle}</Tag>
              <ConfidencePill value={card.confidence} />
              <SourceTierIndicator value={card.source_tier} />
              {card.last_reviewed && (
                <span className="text-white/40 tabular-nums">reviewed {card.last_reviewed}</span>
              )}
              {!card.last_reviewed && card.created && (
                <span className="text-white/30 tabular-nums">created {card.created}</span>
              )}
            </div>
            {!expanded && summary && (
              <p className="text-xs text-white/55 mt-2 leading-relaxed line-clamp-2">{summary}</p>
            )}
          </div>
        </div>
      </header>

      {expanded && (
        <div className="px-5 pb-5 border-t border-white/[0.04] space-y-5">
          {card.tags && card.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-3">
              {card.tags.map((t) => <Tag key={t}>{t}</Tag>)}
            </div>
          )}

          {card.body_markdown && (
            <section className="text-sm">
              <MarkdownRenderer>{linkifyCardIds(card.body_markdown, cardsById, workspace)}</MarkdownRenderer>
            </section>
          )}

          {card.sources && card.sources.length > 0 && (
            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">Sources</h3>
              <ul className="space-y-1.5 text-xs">
                {card.sources.map((s, i) => <SourceRow key={i} source={s} />)}
              </ul>
            </section>
          )}

          {outbound.length > 0 && (
            <ConnectionList
              title="Connects to"
              direction="out"
              connections={outbound}
              cardsById={cardsById}
              workspace={workspace}
            />
          )}

          {inbound.length > 0 && (
            <ConnectionList
              title="Referenced by"
              direction="in"
              connections={inbound}
              cardsById={cardsById}
              workspace={workspace}
            />
          )}

          {(mentions.digests.length > 0 || mentions.articles.length > 0) && (
            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">Mentioned in</h3>
              <ul className="space-y-1 text-xs">
                {mentions.digests.map((d) => (
                  <li key={`d-${d.id}`}>
                    <Link
                      to={`/${workspace}/digests/${d.id}`}
                      className="text-cyan-300 hover:text-cyan-200 underline decoration-cyan-300/30"
                    >
                      Digest · {d.date} · {d.title}
                    </Link>
                  </li>
                ))}
                {mentions.articles.map((a) => (
                  <li key={`a-${a.id}`}>
                    <Link
                      to={`/articles/${a.id}`}
                      className="text-cyan-300 hover:text-cyan-200 underline decoration-cyan-300/30"
                    >
                      Article · {a.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="flex items-center gap-3 pt-2 border-t border-white/[0.04] text-xs">
            <Link
              to={`/${workspace}/knowledge-graph?card=${card.id}`}
              className="inline-flex items-center gap-1.5 text-white/55 hover:text-cyan-200"
            >
              <Network className="h-3.5 w-3.5" />
              Locate in knowledge graph
            </Link>
            <span className="text-white/20">·</span>
            <a
              href={`#${card.id}`}
              className="text-white/40 hover:text-white/70"
              onClick={(e) => {
                e.preventDefault()
                if (typeof navigator !== 'undefined' && navigator.clipboard) {
                  navigator.clipboard.writeText(`${window.location.origin}${window.location.pathname}#${card.id}`)
                }
              }}
              title="Copy anchor link"
            >
              copy anchor
            </a>
            <span className="ml-auto text-white/30 font-mono">{card.id}</span>
          </div>
        </div>
      )}
    </article>
  )
}

function ConnectionList({ title, direction, connections, cardsById, workspace }) {
  // Group by connection type for readability — a card with 8 outbound
  // connections becomes 3 small clusters by type instead of 8 flat rows.
  const byType = new Map()
  for (const c of connections) {
    const key = c.type || '—'
    if (!byType.has(key)) byType.set(key, [])
    byType.get(key).push(c)
  }
  return (
    <section>
      <h3 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">{title}</h3>
      <div className="space-y-2 text-xs">
        {Array.from(byType.entries()).map(([type, list]) => (
          <div key={type} className="flex items-start gap-2 flex-wrap">
            <Tag>{type}</Tag>
            <span className="text-white/30">{direction === 'out' ? '→' : '←'}</span>
            <ul className="flex flex-wrap gap-x-3 gap-y-1 flex-1">
              {list.map((c) => {
                const otherId = direction === 'out' ? c.target : c.source
                const other = cardsById.get(otherId)
                const label = other?.title || otherId
                return (
                  <li key={c.id || `${c.source}-${c.target}-${c.type}`} className="min-w-0">
                    <a
                      href={`#${otherId}`}
                      className="text-cyan-300 hover:text-cyan-200 underline decoration-cyan-300/30 truncate inline-block max-w-full"
                      title={otherId}
                    >
                      {label}
                    </a>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}

function SourceRow({ source }) {
  if (source?.type === 'url' && source.ref) {
    return (
      <li className="text-white/70">
        <a
          href={source.ref}
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-300 hover:text-cyan-200 underline decoration-cyan-300/30"
        >
          {source.title || source.ref}
        </a>
      </li>
    )
  }
  if (source?.type === 'ref') {
    return (
      <li className="text-white/70">
        {source.title || source.ref}
        {source.ref && (
          <code className="ml-2 text-white/40 font-mono text-[0.85em]">{source.ref}</code>
        )}
      </li>
    )
  }
  return <li className="text-white/70">{source?.title || JSON.stringify(source)}</li>
}

