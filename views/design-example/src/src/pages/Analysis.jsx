import { useState } from 'react'

const pages = [
  { id: 'index', label: 'Overview', file: '/archive/isw-analysis/index.html' },
  { id: 'clusters', label: 'Clusters', file: '/archive/isw-analysis/clusters.html' },
  { id: 'themes', label: 'Themes', file: '/archive/isw-analysis/themes.html' },
  { id: 'timeline', label: 'Timeline', file: '/archive/isw-analysis/timeline.html' },
  { id: 'taxonomy', label: 'Taxonomy', file: '/archive/isw-analysis/taxonomy.html' },
  { id: 'gaps', label: 'Gaps', file: '/archive/isw-analysis/gaps.html' },
  { id: 'digests', label: 'Digests', file: '/archive/isw-analysis/digests.html' },
  { id: 'architecture', label: 'Architecture', file: '/archive/isw-analysis/architecture.html' },
]

const knowledgeGraphUrl = '/archive/isw-analysis/knowledge-graph.html'

export default function Analysis() {
  const [tab, setTab] = useState('index')
  const current = pages.find(p => p.id === tab)

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs px-2 py-0.5 rounded-full bg-orange/20 text-orange border border-orange/30">Analysis</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white mb-3">ISW Research Analysis</h1>
        <p className="text-white/80">
          Landscape analysis of the ISW corpus — clusters, taxonomy, gaps, timeline, cross-cutting themes, and knowledge graph.
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-white/[0.06] pb-4">
        {pages.map(p => (
          <button
            key={p.id}
            onClick={() => setTab(p.id)}
            className={`text-sm px-4 py-2 rounded-lg transition-colors font-medium ${
              tab === p.id
                ? 'bg-violet/20 text-violet border border-violet/30'
                : 'text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06]'
            }`}
          >
            {p.label}
          </button>
        ))}
        <a
          href={knowledgeGraphUrl}
          className="text-sm px-4 py-2 rounded-lg transition-colors font-medium text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06] no-underline flex items-center gap-1.5"
        >
          Knowledge Graph <span className="text-[10px] opacity-60">↗</span>
        </a>
      </div>

      {/* Content iframe */}
      <div className="glass rounded-xl overflow-hidden" style={{ minHeight: '80vh' }}>
        <iframe
          key={current.id}
          src={current.file}
          className="w-full border-0"
          style={{ height: '80vh' }}
          title={current.label}
        />
      </div>

      <p className="text-xs text-white/40 mt-4 text-center">
        These analysis pages are generated from the ISW research corpus. 19 knowledge cards · 22 connections · 265+ papers · 14 clusters · 34 digests.
      </p>
    </div>
  )
}
