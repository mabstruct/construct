import { useState } from 'react'

const pages = [
  { id: 'index', label: 'Overview', file: '/archive/architecture/index.html' },
  { id: 'agents', label: 'Agents', file: '/archive/architecture/agents.html' },
  { id: 'pipeline', label: 'Pipeline', file: '/archive/architecture/pipeline.html' },
  { id: 'adaptation', label: 'Adaptation', file: '/archive/architecture/adaptation.html' },
  { id: 'infrastructure', label: 'Infrastructure', file: '/archive/architecture/infrastructure.html' },
  { id: 'dataflow', label: 'Data Flow', file: '/archive/architecture/dataflow.html' },
]

export default function Architecture() {
  const [active, setActive] = useState('index')
  const current = pages.find(p => p.id === active)

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs px-2 py-0.5 rounded-full bg-cyan/20 text-cyan border border-cyan/30">System</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white mb-3">CONSTRUCT Architecture</h1>
        <p className="text-white/80">
          How the autonomous research engine works — multi-agent system, daily pipeline, human-in-the-loop adaptation.
        </p>
      </div>

      {/* Tab nav */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-white/[0.06] pb-4">
        {pages.map(p => (
          <button
            key={p.id}
            onClick={() => setActive(p.id)}
            className={`text-sm px-4 py-2 rounded-lg transition-colors ${
              active === p.id
                ? 'bg-cyan/20 text-cyan border border-cyan/30'
                : 'text-white/40 hover:text-white/60 bg-white/[0.02] border border-white/[0.06]'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Embedded iframe */}
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
        Architecture documentation generated from the CONSTRUCT system specifications.
      </p>
    </div>
  )
}
