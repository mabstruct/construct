import { useMemo, useRef, useCallback } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { useFetch } from '../hooks/useFetch'
import FilterChip from '../components/FilterChip'
import CardSidePanel from '../components/CardSidePanel'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/knowledge-graph
// Spec: spec-v02-views.md §4.5

const EPISTEMIC_TYPES = [
  'finding', 'claim', 'concept', 'method', 'paper',
  'theme', 'gap', 'provocation', 'question', 'connection',
]
const LIFECYCLE_STATES = ['seed', 'growing', 'mature', 'archived']

// 10-colour categorical palette for epistemic types (one per type, stable order).
const TYPE_COLORS = {
  finding:     'rgb(34, 197, 94)',    // green
  claim:       'rgb(234, 179, 8)',    // amber
  concept:     'rgb(99, 102, 241)',   // indigo
  method:      'rgb(56, 189, 248)',   // sky
  paper:       'rgb(168, 85, 247)',   // fuchsia
  theme:       'rgb(244, 114, 182)',  // pink
  gap:         'rgb(220, 38, 38)',    // red
  provocation: 'rgb(249, 115, 22)',   // orange
  question:    'rgb(34, 211, 238)',   // cyan
  connection:  'rgb(163, 163, 163)',  // neutral
}

// 9-colour palette for connection types.
const CONN_COLORS = {
  supports:    'rgba(34, 197, 94, 0.7)',
  extends:     'rgba(56, 189, 248, 0.7)',
  enables:     'rgba(34, 211, 238, 0.7)',
  requires:    'rgba(99, 102, 241, 0.7)',
  inspires:    'rgba(244, 114, 182, 0.7)',
  parallels:   'rgba(168, 85, 247, 0.7)',
  contradicts: 'rgba(220, 38, 38, 0.85)',
  challenges:  'rgba(234, 88, 12, 0.85)',
  'gap-for':   'rgba(234, 179, 8, 0.85)',
}

// Per spec: dashed for contradicts/challenges, dotted for gap-for, solid otherwise.
const CONN_DASH = {
  contradicts: [6, 4],
  challenges:  [6, 4],
  'gap-for':   [1, 4],
}

const NODE_BUDGET = 500
const FADE_ALPHA = 0.1

export default function KnowledgeGraph() {
  const { workspace } = useParams()
  const [params, setParams] = useSearchParams()
  const cards = useFetch(`/data/${workspace}/cards.json`)
  const conns = useFetch(`/data/${workspace}/connections.json`)
  const fgRef = useRef(null)

  const types = params.get('type')?.split(',').filter(Boolean) || []
  const lifecycles = params.get('lifecycle')?.split(',').filter(Boolean) || []
  const selectedCardId = params.get('card')

  const setListParam = (key, list) => {
    const next = new URLSearchParams(params)
    if (list && list.length > 0) next.set(key, list.join(','))
    else next.delete(key)
    setParams(next)
  }
  const clearAllFilters = () => {
    const next = new URLSearchParams()
    if (selectedCardId) next.set('card', selectedCardId)
    setParams(next)
  }
  const setSelected = useCallback((id) => {
    const next = new URLSearchParams(params)
    if (id) next.set('card', id)
    else next.delete('card')
    setParams(next)
  }, [params, setParams])

  const allCards = cards.data?.cards || []
  const allConns = conns.data?.connections || []

  // Per-card connection degree → drives node size.
  const degree = useMemo(() => {
    const d = new Map()
    for (const c of allConns) {
      d.set(c.source, (d.get(c.source) || 0) + 1)
      d.set(c.target, (d.get(c.target) || 0) + 1)
    }
    return d
  }, [allConns])

  // Set of card IDs that pass the current filter (AND across facets, OR within).
  const passingIds = useMemo(() => {
    const set = new Set()
    for (const c of allCards) {
      if (types.length && !types.includes(c.epistemic_type)) continue
      if (lifecycles.length && !lifecycles.includes(c.lifecycle)) continue
      set.add(c.id)
    }
    return set
  }, [allCards, types.join(','), lifecycles.join(',')])

  const hasFilters = types.length > 0 || lifecycles.length > 0

  const graphData = useMemo(() => {
    const nodes = allCards.map((c) => ({
      id: c.id,
      title: c.title,
      type: c.epistemic_type,
      lifecycle: c.lifecycle,
      val: 1 + Math.log10((degree.get(c.id) || 0) + 1) * 4,
    }))
    const links = allConns
      .filter((c) => c.source && c.target)
      .map((c) => ({ source: c.source, target: c.target, type: c.type }))
    return { nodes, links }
  }, [allCards, allConns, degree])

  const focusNode = useCallback((id) => {
    const node = graphData.nodes.find((n) => n.id === id)
    if (!node || !fgRef.current) return
    if (typeof node.x === 'number' && typeof node.y === 'number') {
      fgRef.current.centerAt(node.x, node.y, 600)
      fgRef.current.zoom(2.5, 600)
    }
  }, [graphData])

  const onPanelSelect = (id) => {
    setSelected(id)
    focusNode(id)
  }

  // Epistemic types actually present (drives the legend). Hook must run unconditionally.
  const activeNodeTypes = useMemo(() => {
    const set = new Set(allCards.map((c) => c.epistemic_type).filter(Boolean))
    return EPISTEMIC_TYPES.filter((t) => set.has(t))
  }, [allCards])

  if (cards.loading || conns.loading) return <LoadingState shape="graph" />
  if (cards.error) return <ErrorState message={cards.error.message} />
  if (conns.error) return <ErrorState message={conns.error.message} />

  if (allCards.length === 0) {
    return (
      <div className="py-8">
        <EmptyState
          title="Knowledge graph appears once you have cards."
          message={`Run a research-cycle on ${workspace} to start populating cards.`}
        />
      </div>
    )
  }

  if (allCards.length > NODE_BUDGET) {
    return (
      <div className="py-8">
        <EmptyState
          title={`Graph too large to render interactively (${allCards.length} nodes).`}
          message={`This view supports up to ${NODE_BUDGET} nodes in v0.2. Use filters to narrow, or browse via Artifacts.`}
        />
      </div>
    )
  }

  const selectedCard = allCards.find((c) => c.id === selectedCardId)

  // Connection types actually present in this workspace (for the legend).
  const activeConnTypes = Object.keys(conns.data?.type_counts || {})
    .filter((k) => (conns.data.type_counts[k] || 0) > 0)

  return (
    <div className="py-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h1 className="font-display text-2xl text-white">Knowledge Graph</h1>
        <span className="text-xs text-white/40">
          {passingIds.size} of {allCards.length} cards
          {' · '}
          {graphData.links.length} edges
        </span>
      </div>

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
        {hasFilters && (
          <button
            onClick={clearAllFilters}
            className="text-xs text-white/50 hover:text-white px-2 py-1"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Canvas */}
      <div className="relative rounded-xl border border-white/[0.06] bg-black/40 overflow-hidden h-[calc(100vh-18rem)] min-h-[480px]">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          backgroundColor="transparent"
          cooldownTicks={120}
          nodeRelSize={4}
          nodeVal={(n) => n.val}
          nodeLabel={(n) => `${n.title} · ${n.type}`}
          nodeCanvasObjectMode={() => 'replace'}
          nodeCanvasObject={(node, ctx) => {
            const r = Math.sqrt(Math.max(node.val || 1, 0.5)) * 4
            const passes = !hasFilters || passingIds.has(node.id)
            const isSelected = node.id === selectedCardId
            const base = TYPE_COLORS[node.type] || 'rgb(180,180,180)'
            ctx.beginPath()
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false)
            ctx.fillStyle = withAlpha(base, passes ? 0.9 : FADE_ALPHA)
            ctx.fill()
            if (isSelected) {
              ctx.lineWidth = 2
              ctx.strokeStyle = 'rgba(34, 211, 238, 0.95)'
              ctx.stroke()
            } else if (passes) {
              ctx.lineWidth = 0.6
              ctx.strokeStyle = 'rgba(255,255,255,0.25)'
              ctx.stroke()
            }
          }}
          linkColor={(l) => {
            const sId = l.source.id || l.source
            const tId = l.target.id || l.target
            const passes = !hasFilters || (passingIds.has(sId) && passingIds.has(tId))
            const base = CONN_COLORS[l.type] || 'rgba(255,255,255,0.4)'
            return passes ? base : withAlpha(base, FADE_ALPHA)
          }}
          linkLineDash={(l) => CONN_DASH[l.type] || null}
          linkWidth={(l) => {
            const sId = l.source.id || l.source
            const tId = l.target.id || l.target
            return passingIds.has(sId) && passingIds.has(tId) ? 1.2 : 0.6
          }}
          onNodeClick={(n) => {
            setSelected(n.id)
            focusNode(n.id)
          }}
          onBackgroundClick={() => setSelected(null)}
        />
        {graphData.links.length === 0 && (
          <div className="absolute bottom-3 left-3 text-[10px] text-white/40">
            No connections yet — nodes will repel into a constellation.
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[10px] text-white/50">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-white/30 uppercase tracking-wider">Type</span>
          {activeNodeTypes.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: TYPE_COLORS[t] }} />
              {t}
            </span>
          ))}
        </div>
        {activeConnTypes.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-white/30 uppercase tracking-wider">Edge</span>
            {activeConnTypes.map((t) => (
              <span key={t} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block w-4 h-px"
                  style={{
                    backgroundColor: CONN_COLORS[t] || 'rgba(255,255,255,0.4)',
                    borderTop: CONN_DASH[t]
                      ? `1px ${CONN_DASH[t][1] > 3 ? 'dashed' : 'dotted'} ${CONN_COLORS[t] || 'rgba(255,255,255,0.4)'}`
                      : 'none',
                    height: CONN_DASH[t] ? 0 : 1,
                  }}
                />
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {selectedCard && (
        <CardSidePanel
          card={selectedCard}
          connections={allConns}
          workspace={workspace}
          onClose={() => setSelected(null)}
          onSelect={onPanelSelect}
        />
      )}
    </div>
  )
}

function withAlpha(rgb, alpha) {
  // Accepts `rgb(r,g,b)` or `rgba(r,g,b,a)` — replaces alpha.
  const m = rgb.match(/rgba?\(([^)]+)\)/)
  if (!m) return rgb
  const parts = m[1].split(',').map((s) => s.trim())
  const [r, g, b] = parts
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
