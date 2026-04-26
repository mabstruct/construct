/**
 * Knowledge Graph page — wraps the D3 force-directed graph (archive version)
 * in a full-height iframe. UX features live in the D3 HTML: drag interaction,
 * side panel with card details, edge labels, connection notes, resizable
 * layout, and legend-based type filters (click a card type in the legend to
 * toggle it off/on; hidden types also hide their edges).
 *
 * Data: regenerated on every build from knowledge/cards/*.md and
 * knowledge/connections.json by scripts/sync-and-build.sh (Step 3a).
 * Source of truth: public/archive/isw-analysis/knowledge-graph.html
 */
export default function KnowledgeGraph() {
  return (
    <div className="py-6">
      <div className="mb-6 max-w-5xl mx-auto">
        <h1 className="font-display text-3xl md:text-4xl font-bold text-white mb-2">
          Knowledge Graph
        </h1>
        <p className="text-sm text-white/40">
          25 knowledge cards · 45 typed connections · Force-directed graph with drag interaction
        </p>
      </div>
      <div
        className="w-full rounded-2xl overflow-hidden border border-white/[0.06]"
        style={{ height: 'calc(100vh - 200px)', minHeight: '600px' }}
      >
        <iframe
          src={`${import.meta.env.BASE_URL}archive/isw-analysis/knowledge-graph.html`}
          title="MABSTRUCT Knowledge Graph"
          className="w-full h-full border-0"
          style={{ background: '#0a0a0a' }}
        />
      </div>
    </div>
  )
}
