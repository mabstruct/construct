import { useMemo, useRef, useCallback, useState, useEffect } from 'react'
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
// Visual contract: views/design-example/.../knowledge-graph.html — node
// labels, optional edge labels, drag-to-pin, ego-network highlight on hover.

const EPISTEMIC_TYPES = [
  'finding', 'claim', 'concept', 'method', 'paper',
  'theme', 'gap', 'provocation', 'question', 'connection',
]
const LIFECYCLE_STATES = ['seed', 'growing', 'mature', 'archived']

// 10-colour categorical palette for epistemic types.
const TYPE_COLORS = {
  finding:     'rgb(34, 197, 94)',
  claim:       'rgb(234, 179, 8)',
  concept:     'rgb(99, 102, 241)',
  method:      'rgb(56, 189, 248)',
  paper:       'rgb(168, 85, 247)',
  theme:       'rgb(244, 114, 182)',
  gap:         'rgb(220, 38, 38)',
  provocation: 'rgb(249, 115, 22)',
  question:    'rgb(34, 211, 238)',
  connection:  'rgb(163, 163, 163)',
}

// 9-colour palette for connection types.
const CONN_COLORS = {
  supports:    'rgba(34, 197, 94, 0.85)',
  extends:     'rgba(56, 189, 248, 0.85)',
  enables:     'rgba(34, 211, 238, 0.85)',
  requires:    'rgba(99, 102, 241, 0.85)',
  inspires:    'rgba(244, 114, 182, 0.85)',
  parallels:   'rgba(168, 85, 247, 0.85)',
  contradicts: 'rgba(220, 38, 38, 0.95)',
  challenges:  'rgba(234, 88, 12, 0.95)',
  'gap-for':   'rgba(234, 179, 8, 0.95)',
}

// Per spec: dashed for contradicts/challenges, dotted for gap-for, solid otherwise.
const CONN_DASH = {
  contradicts: [6, 4],
  challenges:  [6, 4],
  'gap-for':   [1, 4],
}

const NODE_BUDGET = 500
const FADE_ALPHA = 0.08
const LABEL_FONT = '500 11px Manrope, system-ui, sans-serif'
const EDGE_LABEL_FONT = '9px Manrope, system-ui, sans-serif'

export default function KnowledgeGraph() {
  const { workspace } = useParams()
  const [params, setParams] = useSearchParams()
  const cards = useFetch(`/data/${workspace}/cards.json`)
  const conns = useFetch(`/data/${workspace}/connections.json`)
  const fgRef = useRef(null)
  const containerRef = useRef(null)

  const [hoveredId, setHoveredId] = useState(null)
  const [showEdgeLabels, setShowEdgeLabels] = useState(false)
  const [showNodeLabels, setShowNodeLabels] = useState(true)
  const [size, setSize] = useState({ w: 0, h: 0 })

  // Track container size so the canvas fills its bounds reactively.
  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0].contentRect
      setSize({ w: rect.width, h: rect.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

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

  // Filter pass-set (AND across facets, OR within).
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

  // Build graphData. The same node objects are reused across renders so the
  // simulation's positions/velocity/fx/fy survive prop updates — this is what
  // makes the experience feel persistent (drag-to-pin actually sticks).
  const graphData = useMemo(() => {
    const nodes = allCards.map((c) => ({
      id: c.id,
      title: c.title,
      type: c.epistemic_type,
      lifecycle: c.lifecycle,
      // Sized by sqrt of degree for visual weight without runaway growth.
      r: 6 + Math.sqrt(degree.get(c.id) || 0) * 2.2,
    }))
    const links = allConns
      .filter((c) => c.source && c.target)
      .map((c) => ({ source: c.source, target: c.target, type: c.type }))
    return { nodes, links }
  }, [allCards, allConns, degree])

  // Adjacency for ego-network highlighting on hover/select.
  const adjacency = useMemo(() => {
    const m = new Map()
    const add = (a, b) => {
      if (!m.has(a)) m.set(a, new Set())
      m.get(a).add(b)
    }
    for (const l of graphData.links) {
      const s = typeof l.source === 'object' ? l.source.id : l.source
      const t = typeof l.target === 'object' ? l.target.id : l.target
      add(s, t)
      add(t, s)
    }
    return m
  }, [graphData])

  // The "spotlight" node — hover takes precedence over selection so passive
  // exploration feels live; otherwise the selected card stays highlighted.
  const spotlightId = hoveredId || selectedCardId

  const focusNode = useCallback((id) => {
    const node = graphData.nodes.find((n) => n.id === id)
    if (!node || !fgRef.current) return
    if (typeof node.x === 'number' && typeof node.y === 'number') {
      fgRef.current.centerAt(node.x, node.y, 600)
      fgRef.current.zoom(2.4, 600)
    }
  }, [graphData])

  // Force tuning matching the design example: spread-out feel, soft centering.
  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    const link = fg.d3Force('link')
    if (link) link.distance(140).strength(0.4)
    const charge = fg.d3Force('charge')
    if (charge) charge.strength(-600)
    fg.d3ReheatSimulation()
  }, [graphData])

  const releaseAll = () => {
    for (const n of graphData.nodes) {
      n.fx = null
      n.fy = null
    }
    if (fgRef.current) fgRef.current.d3ReheatSimulation()
  }

  // Epistemic types actually present (drives the legend). Hook stays unconditional.
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
  const activeConnTypes = Object.keys(conns.data?.type_counts || {})
    .filter((k) => (conns.data.type_counts[k] || 0) > 0)

  // Ego set for the current spotlight (the spotlight + its 1-hop neighbours).
  const egoSet = spotlightId
    ? new Set([spotlightId, ...(adjacency.get(spotlightId) || [])])
    : null

  const isVisible = (nodeId) => !hasFilters || passingIds.has(nodeId)
  const isSpotlit = (nodeId) => !egoSet || egoSet.has(nodeId)

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

        <span className="mx-2 h-4 w-px bg-white/[0.08]" aria-hidden />

        <ToggleButton active={showNodeLabels} onClick={() => setShowNodeLabels(!showNodeLabels)}>
          Labels
        </ToggleButton>
        <ToggleButton active={showEdgeLabels} onClick={() => setShowEdgeLabels(!showEdgeLabels)}>
          Edge labels
        </ToggleButton>
        <button
          onClick={releaseAll}
          className="text-xs text-white/60 hover:text-white px-2.5 py-1 rounded-full border border-white/10 hover:border-white/30"
          title="Release all pinned nodes — let the simulation re-equilibrate"
        >
          Release pins
        </button>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="relative rounded-xl border border-white/[0.06] bg-black/40 overflow-hidden h-[calc(100vh-18rem)] min-h-[480px]"
      >
        {size.w > 0 && (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            width={size.w}
            height={size.h}
            backgroundColor="rgba(0,0,0,0)"
            cooldownTicks={Infinity}
            warmupTicks={40}
            d3VelocityDecay={0.32}
            d3AlphaDecay={0.018}
            nodeRelSize={1}
            nodeLabel={(n) => `${n.title}\n${n.type} · ${n.lifecycle || '—'}`}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.beginPath()
              ctx.arc(node.x, node.y, node.r + 4, 0, 2 * Math.PI)
              ctx.fillStyle = color
              ctx.fill()
            }}
            nodeCanvasObjectMode={() => 'replace'}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const visible = isVisible(node.id)
              const spotlit = isSpotlit(node.id)
              const isSelected = node.id === selectedCardId
              const isHovered = node.id === hoveredId
              const baseColor = TYPE_COLORS[node.type] || 'rgb(180,180,180)'

              const alpha = !visible
                ? FADE_ALPHA
                : !spotlit
                  ? 0.18
                  : isHovered || isSelected
                    ? 1.0
                    : 0.92

              // Glow for the spotlight node.
              if (visible && (isHovered || isSelected)) {
                ctx.save()
                ctx.shadowColor = baseColor
                ctx.shadowBlur = 18
                ctx.beginPath()
                ctx.arc(node.x, node.y, node.r, 0, 2 * Math.PI)
                ctx.fillStyle = withAlpha(baseColor, alpha)
                ctx.fill()
                ctx.restore()
              } else {
                ctx.beginPath()
                ctx.arc(node.x, node.y, node.r, 0, 2 * Math.PI)
                ctx.fillStyle = withAlpha(baseColor, alpha)
                ctx.fill()
              }

              // Stroke ring — heavier for selected, lighter for hover, thin otherwise.
              ctx.lineWidth = isSelected ? 2.4 : isHovered ? 1.8 : 0.7
              ctx.strokeStyle = isSelected
                ? 'rgba(34, 211, 238, 0.95)'
                : withAlpha(brighten(baseColor), visible ? 0.55 : FADE_ALPHA * 2)
              ctx.stroke()

              // Pin indicator — a small dot at the upper-right when fx/fy are set.
              if (node.fx != null && node.fy != null) {
                ctx.beginPath()
                ctx.arc(node.x + node.r * 0.7, node.y - node.r * 0.7, 1.6, 0, 2 * Math.PI)
                ctx.fillStyle = 'rgba(255,255,255,0.85)'
                ctx.fill()
              }

              // Label below the node — clipped at view-scale to avoid clutter.
              if (showNodeLabels && visible && globalScale > 0.5) {
                const label = node.title.length > 32 ? node.title.slice(0, 30) + '…' : node.title
                ctx.font = LABEL_FONT
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.fillStyle = isHovered || isSelected
                  ? 'rgba(255,255,255,0.95)'
                  : `rgba(220,228,238,${spotlit ? 0.7 : 0.35})`
                ctx.fillText(label, node.x, node.y + node.r + 4)
              }
            }}
            linkColor={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              const visible = isVisible(sId) && isVisible(tId)
              const spotlit = !egoSet || (egoSet.has(sId) && egoSet.has(tId))
              const base = CONN_COLORS[l.type] || 'rgba(255,255,255,0.4)'
              if (!visible) return withAlpha(base, FADE_ALPHA)
              if (!spotlit) return withAlpha(base, 0.12)
              return base
            }}
            linkLineDash={(l) => CONN_DASH[l.type] || null}
            linkWidth={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              const visible = isVisible(sId) && isVisible(tId)
              const spotlit = !egoSet || (egoSet.has(sId) && egoSet.has(tId))
              if (!visible) return 0.4
              return spotlit ? 1.8 : 0.7
            }}
            linkDirectionalArrowLength={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              return isVisible(sId) && isVisible(tId) ? 4 : 0
            }}
            linkDirectionalArrowRelPos={1}
            linkCanvasObjectMode={() => (showEdgeLabels ? 'after' : undefined)}
            linkCanvasObject={(link, ctx, globalScale) => {
              if (!showEdgeLabels) return
              const sId = link.source.id || link.source
              const tId = link.target.id || link.target
              if (!isVisible(sId) || !isVisible(tId)) return
              if (egoSet && !(egoSet.has(sId) && egoSet.has(tId))) return
              if (globalScale < 0.7) return
              const sx = link.source.x, sy = link.source.y
              const tx = link.target.x, ty = link.target.y
              if (sx == null || tx == null) return
              const mx = (sx + tx) / 2
              const my = (sy + ty) / 2 - 4
              ctx.font = EDGE_LABEL_FONT
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'
              ctx.fillStyle = withAlpha(CONN_COLORS[link.type] || 'rgba(255,255,255,0.6)', 0.95)
              ctx.fillText(link.type, mx, my)
            }}
            onNodeClick={(n) => {
              setSelected(n.id)
              focusNode(n.id)
            }}
            onNodeHover={(n) => setHoveredId(n ? n.id : null)}
            onNodeDragEnd={(n) => {
              // Pin the node where the user left it. The simulation keeps
              // running for everything else, so the layout adapts around the pin.
              n.fx = n.x
              n.fy = n.y
            }}
            onBackgroundClick={() => setSelected(null)}
          />
        )}
        {graphData.links.length === 0 && (
          <div className="absolute bottom-3 left-3 text-[10px] text-white/40">
            No connections yet — nodes will repel into a constellation.
          </div>
        )}
        <div className="absolute top-2 right-3 text-[10px] text-white/30 pointer-events-none">
          drag to reposition · scroll to zoom · click to inspect
        </div>
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
                <EdgeSwatch type={t} />
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
          onSelect={(id) => { setSelected(id); focusNode(id) }}
        />
      )}
    </div>
  )
}

function ToggleButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
        active
          ? 'border-cyan-400/40 bg-cyan-400/10 text-white'
          : 'border-white/10 bg-white/[0.04] text-white/60 hover:bg-white/[0.08]'
      }`}
    >
      {children}
    </button>
  )
}

function EdgeSwatch({ type }) {
  const color = CONN_COLORS[type] || 'rgba(255,255,255,0.4)'
  const dash = CONN_DASH[type]
  // Render dashed/dotted via SVG — CSS borders don't reliably emulate the
  // canvas linkLineDash patterns at thin widths.
  return (
    <svg width="20" height="6" aria-hidden>
      <line
        x1="0" y1="3" x2="20" y2="3"
        stroke={color}
        strokeWidth="1.4"
        strokeDasharray={dash ? dash.join(',') : undefined}
      />
    </svg>
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

function brighten(rgb) {
  // Lift each channel ~30% toward white for the stroke ring.
  const m = rgb.match(/rgba?\(([^)]+)\)/)
  if (!m) return rgb
  const parts = m[1].split(',').map((s) => s.trim())
  const [r, g, b] = parts.map(Number)
  const lift = (v) => Math.min(255, Math.round(v + (255 - v) * 0.35))
  return `rgb(${lift(r)}, ${lift(g)}, ${lift(b)})`
}
