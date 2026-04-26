import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import articles from '../data/articles.json'

const registerColors = {
  research: { color: '#00d9ff', label: 'research' },
  reflection: { color: '#a855f7', label: 'reflection' },
  constructing: { color: '#fb923c', label: 'constructing' },
  inference: { color: '#10b981', label: 'inference' },
  synthesis: { color: '#f43f5e', label: 'synthesis' },
}

const defaultRegisterColor = { color: '#9CA3AF', label: 'other' }

const domainColors = {
  math: { color: '#00d9ff', label: 'Mathematics' },
  ai: { color: '#a855f7', label: 'AI & Agents' },
  awareness: { color: '#fb923c', label: 'Awareness' },
  cosmology: { color: '#f43f5e', label: 'Cosmology' },
}

const defaultDomainColor = { color: '#9CA3AF', label: 'Other' }

export default function Blog() {
  const [domainFilter, setDomainFilter] = useState('all')
  const [registerFilter, setRegisterFilter] = useState('all')
  const [monthFilter, setMonthFilter] = useState('all')

  const allDomains = useMemo(() => {
    const set = new Set()
    articles.forEach(a => a.domains.forEach(d => set.add(d)))
    return [...set].sort()
  }, [])

  const allRegisters = useMemo(() => [...new Set(articles.map(a => a.register))].sort(), [])

  const allMonths = useMemo(() => {
    const set = new Set()
    articles.forEach(a => {
      const d = new Date(a.date)
      set.add(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
    })
    return [...set].sort().reverse()
  }, [])

  const filtered = useMemo(() => {
    return articles.filter(a => {
      if (domainFilter !== 'all' && !a.domains.includes(domainFilter)) return false
      if (registerFilter !== 'all' && a.register !== registerFilter) return false
      if (monthFilter !== 'all') {
        const d = new Date(a.date)
        const m = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
        if (m !== monthFilter) return false
      }
      return true
    })
  }, [domainFilter, registerFilter, monthFilter])

  const monthLabel = (m) => {
    const [y, mo] = m.split('-')
    const names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    return `${names[parseInt(mo)]} ${y}`
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs px-2 py-0.5 rounded-full border text-white" style={{ color: '#a855f7', borderColor: 'rgba(168, 85, 247, 0.4)', backgroundColor: 'rgba(168, 85, 247, 0.18)' }}>Writing</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white mb-3">Thought Stream</h1>
        <p className="text-white/50 text-lg leading-relaxed">
          Ideas, essays, and reflections across mathematics, cosmology, philosophy, arts, and AI — indexed by date, register, and domain.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-white">{articles.length}</div>
          <div className="text-xs text-white/40 mt-0.5">Blog Posts</div>
        </div>
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold" style={{ color: '#00d9ff' }}>{allDomains.length}</div>
          <div className="text-xs text-white/40 mt-0.5">Domains</div>
        </div>
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold" style={{ color: '#a855f7' }}>{allRegisters.length}</div>
          <div className="text-xs text-white/40 mt-0.5">Registers</div>
        </div>
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold" style={{ color: '#fb923c' }}>{allMonths.length}</div>
          <div className="text-xs text-white/40 mt-0.5">Months</div>
        </div>
      </div>

      {/* Filters */}
      <div className="space-y-3 mb-8">
        {/* Domain filter */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-white/30 w-16">Domain</span>
          <button
            onClick={() => setDomainFilter('all')}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              domainFilter === 'all' ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
            }`}
          >All</button>
          {allDomains.map(d => {
            const c = domainColors[d]
            return (
              <button
                key={d}
                onClick={() => setDomainFilter(d)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  domainFilter === d ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
                }`}
              >{c.label}</button>
            )
          })}
        </div>

        {/* Register filter */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-white/30 w-16">Register</span>
          <button
            onClick={() => setRegisterFilter('all')}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              registerFilter === 'all' ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
            }`}
          >All</button>
          {allRegisters.map(r => {
            return (
              <button
                key={r}
                onClick={() => setRegisterFilter(r)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  registerFilter === r ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
                }`}
              >{r}</button>
            )
          })}
        </div>

        {/* Month filter */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-white/30 w-16">Month</span>
          <button
            onClick={() => setMonthFilter('all')}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              monthFilter === 'all' ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
            }`}
          >All</button>
          {allMonths.map(m => (
            <button
              key={m}
              onClick={() => setMonthFilter(m)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                monthFilter === m ? 'bg-white/10 text-white border-white/20' : 'border-white/[0.06] bg-white/[0.02] text-white/40 hover:border-white/20'
              }`}
            >{monthLabel(m)}</button>
          ))}
        </div>
      </div>

      {/* Results count */}
      <div className="text-xs text-white/30 mb-4">
        Showing {filtered.length} of {articles.length} articles
      </div>

      {/* Article list */}
      <div className="space-y-3">
        {filtered.map(a => {
          const rc = registerColors[a.register] || defaultRegisterColor
          return (
            <Link
              key={a.id}
              to={`/thought-stream/${a.id}`}
              className="glass glass-hover rounded-xl p-5 transition-all group block"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-mono text-white/80">{a.date}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full text-white border" style={{ color: rc.color, borderColor: `${rc.color}40`, backgroundColor: `${rc.color}18` }}>
                    {a.register}
                  </span>
                  {a.domains.map(d => {
                    const dc = domainColors[d] || defaultDomainColor
                    return (
                      <span key={d} className="text-[10px] px-2 py-0.5 rounded-full text-white border" style={{ color: dc.color, borderColor: `${dc.color}40`, backgroundColor: `${dc.color}18` }}>
                        {dc.label}
                      </span>
                    )
                  })}
                </div>
                <svg className="w-4 h-4 text-white/40 group-hover:text-white/80 transition-colors flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>

              <h2 className="text-lg font-semibold font-display text-white group-hover:text-white/80 transition-colors mb-1.5">
                {a.title}
              </h2>

              {a.subtitle && (
                <p className="text-sm text-white/50 italic mb-2">{a.subtitle.replace(/^\*|\*$/g, '')}</p>
              )}

              <p className="text-sm text-white/50 leading-relaxed line-clamp-2">{a.summary}</p>
            </Link>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-white/30">
          No articles match the current filters.
        </div>
      )}
    </div>
  )
}
