import { useMemo, useRef, useCallback, useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { forceCollide } from 'd3-force'
import { useFetch } from '../hooks/useFetch'
import FilterChip from '../components/FilterChip'
import CardSidePanel from '../components/CardSidePanel'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /:workspace/knowledge-graph
// Spec: spec-v02-views.md §4.5 (route) and spec-v02-knowledge-views-spike.md
// §2.3–§2.4 (Spike A locked 2026-04-30 — restyle, layout-dynamics fixes,
// design-example colour palette, click-to-toggle legend, auto-on edge
// labels under 30 edges).
// Visual reference: views/design-example/.../knowledge-graph.html.

const EPISTEMIC_TYPES = [
  'finding', 'claim', 'concept', 'method', 'paper',
  'theme', 'gap', 'provocation', 'question', 'connection',
]
const LIFECYCLE_STATES = ['seed', 'growing', 'mature', 'archived']

// Type palette aligned with views/design-example badge colours (the canonical
// 6 — theme/provocation/finding/gap/method/weird) plus 4 distinct extensions
// for the types we carry beyond the design example.
const TYPE_COLORS = {
  theme:       'rgb(96, 165, 250)',   // #60a5fa  blue
  provocation: 'rgb(192, 132, 252)',  // #c084fc  purple
  finding:     'rgb(74, 222, 128)',   // #4ade80  green
  gap:         'rgb(251, 191, 36)',   // #fbbf24  amber
  method:      'rgb(34, 211, 238)',   // #22d3ee  cyan
  // Extensions — distinct hues that read against the canonical 6
  claim:       'rgb(250, 204, 21)',   // #facc15  yellow
  concept:     'rgb(129, 140, 248)',  // #818cf8  indigo
  paper:       'rgb(167, 139, 250)',  // #a78bfa  violet
  question:    'rgb(94, 234, 212)',   // #5eead4  teal
  connection:  'rgb(148, 163, 184)',  // #94a3b8  slate (neutral default)
}

// Connection palette — supports/extends/parallels/requires lifted from the
// design example's `.conn-type-*` rules; the four we carry beyond the
// design example (enables/inspires/challenges/gap-for) get adjacent hues.
const CONN_COLORS = {
  supports:    'rgba(74, 222, 128, 0.85)',    // green
  extends:     'rgba(96, 165, 250, 0.85)',    // blue
  enables:     'rgba(34, 211, 238, 0.85)',    // cyan
  requires:    'rgba(192, 132, 252, 0.85)',   // purple
  inspires:    'rgba(244, 114, 182, 0.85)',   // pink
  parallels:   'rgba(251, 191, 36, 0.85)',    // amber
  contradicts: 'rgba(248, 113, 113, 0.95)',   // red
  challenges:  'rgba(251, 146, 60, 0.95)',    // orange
  'gap-for':   'rgba(234, 179, 8, 0.95)',     // gold
}

// Per spec: dashed for contradicts/challenges, dotted for gap-for, solid otherwise.
const CONN_DASH = {
  contradicts: [6, 4],
  challenges:  [6, 4],
  'gap-for':   [1, 4],
}

const NODE_BUDGET = 500
// Three-tier alpha for edges (spec §2.4): spotlit / ambient / dimmed.
// Locked values from spec-v02-knowledge-views-spike.md §2.4.
const SPOTLIT_ALPHA = 0.85
const AMBIENT_ALPHA = 0.22
const DIM_ALPHA = 0.07
const EDGE_LABEL_AUTO_THRESHOLD = 30   // auto-on when links.length ≤ 30 (Q-A1)
// Label font sizes are *screen* pixels — the canvas font is set per-frame
// as `${SIZE / globalScale}px` so labels stay constant on screen regardless
// of zoom (see nodeCanvasObject / linkCanvasObject below).
const NODE_LABEL_SCREEN_PX = 10
const EDGE_LABEL_SCREEN_PX = 9
const NODE_STROKE_DEFAULT = 'rgba(68, 85, 102, 0.85)'  // #445566 from design example
const CANVAS_BG = '#0a0e17'                            // matches design example shell

export default function KnowledgeGraph() {
  const { workspace } = useParams()
  const [params, setParams] = useSearchParams()
  const cards = useFetch(`/data/${workspace}/cards.json`)
  const conns = useFetch(`/data/${workspace}/connections.json`)
  const fgRef = useRef(null)
  const containerRef = useRef(null)

  const [hoveredId, setHoveredId] = useState(null)
  // Default decided once when conns load (Q-A1: auto-on when ≤ 30 edges).
  // null = not yet seeded; once seeded, user toggles persist.
  const [showEdgeLabels, setShowEdgeLabels] = useState(null)
  const [showNodeLabels, setShowNodeLabels] = useState(true)
  const [size, setSize] = useState({ w: 0, h: 0 })

  // Track container size so the canvas fills its bounds reactively.
  // Deps include loading flags because the container only enters the DOM
  // after the early-return loading branch resolves; without re-running, the
  // observer would attach to a null ref and the canvas would never mount.
  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0].contentRect
      setSize({ w: rect.width, h: rect.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [cards.loading, conns.loading])

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
  //
  // Cross-workspace edge guard: connections.json contains references to
  // cards in OTHER workspaces (a connection in cosmology may target a card
  // that lives in philosophy-of-physics). Per spec-v02-views.md §4.5,
  // cross-workspace KG is deferred to v0.2.1; the v0.2 view is single-
  // workspace. If we keep these phantom-targeted links, d3-force's link
  // force throws "node not found" on initialize, leaves the force in a
  // half-state, and every subsequent tick errors with "Attempted to assign
  // to readonly property" when it tries to mutate undefined node positions.
  // That is what blanks the canvas during drag.
  const graphData = useMemo(() => {
    const nodes = allCards.map((c) => ({
      id: c.id,
      title: c.title,
      type: c.epistemic_type,
      lifecycle: c.lifecycle,
      // Spec §2.3 D3: shrunk radius caps around 12px instead of the previous
      // 22px, keeping nodes from touching at the 33-card / 50-edge scale.
      r: 4 + Math.sqrt(degree.get(c.id) || 0) * 1.4,
    }))
    const nodeIds = new Set(nodes.map((n) => n.id))
    const links = allConns
      .filter((c) => c.source && c.target)
      .filter((c) => nodeIds.has(c.source) && nodeIds.has(c.target))
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

  // Force tuning — locked spec values (§2.3): charge -1400 + d3-force collision
  // with `r + 4` padding so nodes stop overlapping at the chosen radius. The
  // earlier "canvas blanks on drag" failure that pushed us to charge=-700 +
  // no-collision was caused by cross-workspace edges referencing absent
  // nodes (now filtered in graphData), not by these forces themselves.
  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    const link = fg.d3Force('link')
    if (link) link.distance(140).strength(0.4)
    const charge = fg.d3Force('charge')
    if (charge) charge.strength(-1400)
    fg.d3Force('collision', forceCollide().radius((n) => n.r + 4).strength(1))
    fg.d3ReheatSimulation()
  }, [graphData])

  // Seed showEdgeLabels once per dataset based on edge count (Q-A1 auto-on
  // threshold). After the first seed the user's toggle wins.
  useEffect(() => {
    if (showEdgeLabels === null && graphData.links.length > 0) {
      setShowEdgeLabels(graphData.links.length <= EDGE_LABEL_AUTO_THRESHOLD)
    }
  }, [graphData.links.length, showEdgeLabels])

  // One-shot fit-to-view per dataset, fired by onEngineStop (spec §2.3).
  // Subsequent reheats (drag-pin, release-pins) keep this gate true so the
  // user's chosen viewport isn't yanked back to fit on every interaction.
  const fittedRef = useRef(false)
  useEffect(() => {
    fittedRef.current = false
  }, [graphData])
  const handleEngineStop = useCallback(() => {
    if (fittedRef.current) return
    fittedRef.current = true
    if (fgRef.current) fgRef.current.zoomToFit(600, 40)
  }, [])

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

      {/* Canvas — design-example deep navy shell (#0a0e17) */}
      <div
        ref={containerRef}
        className="relative rounded-xl border border-white/[0.06] overflow-hidden h-[calc(100vh-18rem)] min-h-[480px]"
        style={{ backgroundColor: CANVAS_BG }}
      >
        {size.w > 0 && (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            width={size.w}
            height={size.h}
            backgroundColor="rgba(0,0,0,0)"
            cooldownTicks={150}
            warmupTicks={40}
            onEngineStop={handleEngineStop}
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
              const baseColor = TYPE_COLORS[node.type] || 'rgb(148, 163, 184)'

              const alpha = !visible
                ? DIM_ALPHA
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

              // Stroke ring — selected gets a cyan accent; otherwise a muted
              // slate matching the design example's `marker path { fill: #445566 }`.
              ctx.lineWidth = isSelected ? 2.4 : isHovered ? 1.8 : 0.8
              ctx.strokeStyle = isSelected
                ? 'rgba(34, 211, 238, 0.95)'
                : visible
                  ? NODE_STROKE_DEFAULT
                  : withAlpha(NODE_STROKE_DEFAULT, DIM_ALPHA * 2)
              ctx.stroke()

              // Pin indicator — a small dot at the upper-right when fx/fy are set.
              if (node.fx != null && node.fy != null) {
                ctx.beginPath()
                ctx.arc(node.x + node.r * 0.7, node.y - node.r * 0.7, 1.6, 0, 2 * Math.PI)
                ctx.fillStyle = 'rgba(255,255,255,0.85)'
                ctx.fill()
              }

              // Label rendering — locked rules from spec §2.4:
              //   1. Ego-set always shows (hovered/selected node + 1-hop)
              //   2. Ambient mode shows labels only when globalScale > 1.0
              //      so the rest-state stays readable
              //   3. Font is sized in *screen* pixels, not world. Canvas
              //      ctx.font specifies world units, so to keep a constant
              //      10-screen-pixel label we divide by globalScale. This is
              //      what made labels look "huge" before — they were world-
              //      unit sized, scaling with the view.
              const inEgo = egoSet && egoSet.has(node.id)
              const ambientShow = !egoSet && globalScale > 1.0
              const labelAllowed = showNodeLabels && visible && (inEgo || ambientShow)
              if (labelAllowed) {
                const label = node.title.length > 32 ? node.title.slice(0, 30) + '…' : node.title
                const fontWorldPx = NODE_LABEL_SCREEN_PX / globalScale
                const offsetWorldPx = 4 / globalScale
                const strokeWorldPx = 2 / globalScale
                ctx.font = `500 ${fontWorldPx}px Manrope, system-ui, sans-serif`
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.lineWidth = strokeWorldPx
                ctx.strokeStyle = 'rgba(10, 14, 23, 0.9)'
                ctx.strokeText(label, node.x, node.y + node.r + offsetWorldPx)
                ctx.fillStyle = isHovered || isSelected
                  ? 'rgba(255,255,255,0.95)'
                  : `rgba(220,228,238,${inEgo ? 0.9 : 0.6})`
                ctx.fillText(label, node.x, node.y + node.r + offsetWorldPx)
              }
            }}
            linkColor={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              const visible = isVisible(sId) && isVisible(tId)
              const base = CONN_COLORS[l.type] || 'rgba(200, 215, 230, 0.85)'
              if (!visible) return withAlpha(base, DIM_ALPHA)
              // Three tiers (spec §2.4): no spotlight = ambient, in spotlight
              // = full base alpha, outside spotlight = dimmed.
              if (!egoSet) return withAlpha(base, AMBIENT_ALPHA)
              if (egoSet.has(sId) && egoSet.has(tId)) return withAlpha(base, SPOTLIT_ALPHA)
              return withAlpha(base, DIM_ALPHA)
            }}
            linkLineDash={(l) => CONN_DASH[l.type] || null}
            linkWidth={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              const visible = isVisible(sId) && isVisible(tId)
              if (!visible) return 0.4
              if (!egoSet) return 1.2
              if (egoSet.has(sId) && egoSet.has(tId)) return 2.0
              return 0.6
            }}
            linkDirectionalArrowLength={(l) => {
              const sId = l.source.id || l.source
              const tId = l.target.id || l.target
              return isVisible(sId) && isVisible(tId) ? 4 : 0
            }}
            linkDirectionalArrowRelPos={1}
            // Always 'after' so the library's default link rendering runs
            // first; our custom paint just adds edge labels on top when
            // toggled. Returning undefined here previously caused the
            // library to skip default rendering entirely — that's the bug
            // where no edges appeared at all.
            linkCanvasObjectMode={() => 'after'}
            linkCanvasObject={(link, ctx, globalScale) => {
              if (!showEdgeLabels) return
              const sId = link.source.id || link.source
              const tId = link.target.id || link.target
              if (!isVisible(sId) || !isVisible(tId)) return
              if (egoSet && !(egoSet.has(sId) && egoSet.has(tId))) return
              if (globalScale < 1.0) return
              const sx = link.source.x, sy = link.source.y
              const tx = link.target.x, ty = link.target.y
              if (sx == null || tx == null) return
              const mx = (sx + tx) / 2
              const my = (sy + ty) / 2 - 4 / globalScale
              // Edge label font in screen-px; same scale-inverse trick as
              // node labels so size is constant regardless of zoom.
              const fontWorldPx = EDGE_LABEL_SCREEN_PX / globalScale
              ctx.font = `${fontWorldPx}px Manrope, system-ui, sans-serif`
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

      {/* Legend — Type swatches are clickable, toggling the ?type= URL list
          (Q-A5). Edge swatches stay read-only; connection type filtering is
          out of scope for this slice. */}
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[10px] text-white/50">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-white/30 uppercase tracking-wider">Type</span>
          {activeNodeTypes.map((t) => {
            const filterActive = types.length > 0
            const isOn = !filterActive || types.includes(t)
            return (
              <button
                key={t}
                type="button"
                onClick={() => {
                  const next = types.includes(t)
                    ? types.filter((x) => x !== t)
                    : [...types, t]
                  setListParam('type', next)
                }}
                aria-pressed={filterActive && types.includes(t)}
                className={`inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded transition-colors ${
                  isOn
                    ? 'text-white/75 hover:bg-white/[0.06]'
                    : 'text-white/30 hover:text-white/55 hover:bg-white/[0.04]'
                }`}
                title={
                  types.includes(t)
                    ? `Remove ${t} from filter`
                    : filterActive
                      ? `Add ${t} to filter`
                      : `Show only ${t}`
                }
              >
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{
                    backgroundColor: TYPE_COLORS[t],
                    opacity: isOn ? 1 : 0.35,
                  }}
                />
                {t}
              </button>
            )
          })}
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
