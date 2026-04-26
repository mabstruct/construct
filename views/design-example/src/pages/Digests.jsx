import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import digests from '../data/digests.json'

const clusterColors = {
  'intent-to-action': '#00d9ff',
  'embodied-ai': '#10b981',
  'indoor-world-model': '#a855f7',
  'causal-world-models': '#ff8c42',
  'robot-learning': '#facc15',
  'spatial-understanding': '#a855f7',
  'vision-language': '#f43f5e',
  'agentic-systems': '#10b981',
  'perception-detection': '#ff8c42',
  'agentic-robot-middleware': '#00d9ff',
  'spatial-rag-robotics': '#a855f7',
  'foundations-training': 'rgba(255, 255, 255, 0.3)',
  'robot-navigation': 'rgba(255, 255, 255, 0.3)',
}

export default function Digests() {
  const [cluster, setCluster] = useState('all')

  const allClusters = useMemo(() => {
    const set = new Set()
    digests.forEach(d => d.candidates.forEach(c => { if (c.cluster) set.add(c.cluster) }))
    return [...set].sort()
  }, [])

  const filtered = useMemo(() => {
    if (cluster === 'all') return digests
    return digests.map(d => ({
      ...d,
      candidates: d.candidates.filter(c => c.cluster === cluster)
    })).filter(d => d.candidates.length > 0)
  }, [cluster])

  const totalPapers = digests.reduce((s, d) => s + d.candidates.length, 0)
  const topRated = digests.reduce((s, d) => s + d.candidates.filter(c => c.relevance >= 5).length, 0)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs px-2 py-0.5 rounded-full bg-cyan/20 text-cyan border border-cyan/30">Daily</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white mb-3">ISW Research Digests</h1>
        <p className="text-white/80">
          Daily automated research digests from the Intelligent Systems & Worlds domain.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="glass rounded-lg p-4 text-center border border-white/[0.08]">
          <div className="text-2xl font-bold text-cyan">{digests.length}</div>
          <div className="text-xs text-white/40 mt-1">Digests</div>
        </div>
        <div className="glass rounded-lg p-4 text-center border border-white/[0.08]">
          <div className="text-2xl font-bold text-violet">{totalPapers}</div>
          <div className="text-xs text-white/40 mt-1">Papers Found</div>
        </div>
        <div className="glass rounded-lg p-4 text-center border border-white/[0.08]">
          <div className="text-2xl font-bold text-orange">{topRated}</div>
          <div className="text-xs text-white/40 mt-1">Top Rated</div>
        </div>
      </div>

      {/* Cluster filter */}
      <div className="mb-6 flex flex-wrap gap-2">
        <button
          onClick={() => setCluster('all')}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
            cluster === 'all'
              ? 'border-white/20 bg-white/[0.1] text-white'
              : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
          }`}
        >
          All clusters
        </button>
        {allClusters.map(c => (
          <button
            key={c}
            onClick={() => setCluster(c)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              cluster === c
                ? 'border-white/20 bg-white/[0.1] text-white'
                : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Digest list */}
      <div className="space-y-3">
        {filtered.map(d => (
          <Link
            key={d.date}
            to={`/digests/${d.date}`}
            className="block glass glass-hover border border-white/[0.08] rounded-xl p-5 hover:border-white/20 transition-all group"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-mono text-cyan">{d.date}</span>
                <span className="text-xs text-white/50">
                  {d.candidates.length} candidates
                </span>
              </div>
              <div className="flex items-center gap-1">
                {d.candidates.filter(c => c.relevance >= 5).length > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-orange/10 text-orange border border-orange/20">
                    {d.candidates.filter(c => c.relevance >= 5).length} top
                  </span>
                )}
                <svg className="w-4 h-4 text-white/40 group-hover:text-cyan transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
            {d.theme && (
              <p className="text-sm text-white/80 mb-3 line-clamp-2">{d.theme}</p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {[...new Set(d.candidates.map(c => c.cluster).filter(Boolean))].map(c => (
                <span key={c} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-white/40">
                  {c}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
