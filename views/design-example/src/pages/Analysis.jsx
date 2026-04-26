import { useState } from 'react'
import ISWLandscape from '../components/ISWLandscape'

const htmlPages = [
  { id: 'index', label: 'Overview', file: '/archive/isw-analysis/index.html' },
  { id: 'clusters', label: 'Clusters', file: '/archive/isw-analysis/clusters.html' },
  { id: 'timeline', label: 'Timeline', file: '/archive/isw-analysis/timeline.html' },
  { id: 'taxonomy', label: 'Taxonomy', file: '/archive/isw-analysis/taxonomy.html' },
  { id: 'gaps', label: 'Gaps', file: '/archive/isw-analysis/gaps.html' },
  { id: 'digests', label: 'Digests', file: '/archive/isw-analysis/digests.html' },
  { id: 'architecture', label: 'Architecture', file: '/archive/isw-analysis/architecture.html' },
]

export default function Analysis() {
  const [mode, setMode] = useState('interactive')
  const [htmlTab, setHtmlTab] = useState('index')
  const currentHtml = htmlPages.find(p => p.id === htmlTab)

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs px-2 py-0.5 rounded-full bg-orange/20 text-orange border border-orange/30">Analysis</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white mb-3">ISW Research Analysis</h1>
        <p className="text-white/80">
          Landscape analysis of the ISW corpus — clusters, taxonomy, gaps, timeline, and cross-cutting themes.
        </p>
      </div>

      {/* Mode toggle: Interactive vs Archive */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setMode('interactive')}
          className={`text-sm px-5 py-2.5 rounded-lg transition-colors font-medium ${
            mode === 'interactive'
              ? 'bg-violet/20 text-violet border border-violet/30'
              : 'text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06]'
          }`}
        >
          Interactive
        </button>
        <button
          onClick={() => setMode('archive')}
          className={`text-sm px-5 py-2.5 rounded-lg transition-colors font-medium ${
            mode === 'archive'
              ? 'bg-orange/20 text-orange border border-orange/30'
              : 'text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06]'
          }`}
        >
          HTML Archive
        </button>
      </div>

      {/* Interactive mode */}
      {mode === 'interactive' && (
        <ISWLandscape />
      )}

      {/* Archive mode */}
      {mode === 'archive' && (
        <>
          <div className="flex flex-wrap gap-2 mb-6 border-b border-white/[0.06] pb-4">
            {htmlPages.map(p => (
              <button
                key={p.id}
                onClick={() => setHtmlTab(p.id)}
                className={`text-sm px-4 py-2 rounded-lg transition-colors ${
                  htmlTab === p.id
                    ? 'bg-orange/20 text-orange border border-orange/30'
                    : 'text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="glass rounded-xl overflow-hidden" style={{ minHeight: '80vh' }}>
            <iframe
              key={currentHtml.id}
              src={currentHtml.file}
              className="w-full border-0"
              style={{ height: '80vh' }}
              title={currentHtml.label}
            />
          </div>

          <p className="text-xs text-white/40 mt-4 text-center">
            These analysis pages are self-contained HTML documents generated from the ISW research corpus.
          </p>
        </>
      )}
    </div>
  )
}
