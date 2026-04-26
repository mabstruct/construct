import { useParams, Link } from 'react-router-dom'
import digests from '../data/digests.json'

const relevanceColor = (r) => {
  if (r >= 5) return 'text-orange'
  if (r >= 4) return 'text-cyan'
  if (r >= 3) return 'text-white/30'
  return 'text-white/20'
}

export default function DigestDetail() {
  const { date } = useParams()
  const digest = digests.find(d => d.date === date)

  if (!digest) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 text-center">
        <h1 className="text-2xl font-bold text-white mb-4">Digest not found</h1>
        <Link to="/digests" className="text-cyan hover:underline">Back to digests</Link>
      </div>
    )
  }

  const idx = digests.findIndex(d => d.date === date)
  const prev = idx < digests.length - 1 ? digests[idx + 1] : null
  const next = idx > 0 ? digests[idx - 1] : null

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-white/50 mb-6">
        <Link to="/digests" className="hover:text-cyan transition-colors">Digests</Link>
        <span>/</span>
        <span className="text-white">{date}</span>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold font-display text-white mb-3">
          Research Digest — {date}
        </h1>
        {digest.theme && (
          <div className="glass border border-white/[0.08] rounded-lg p-4 mt-4">
            <div className="text-xs text-white/40 mb-1">Theme</div>
            <p className="text-sm text-white leading-relaxed">{digest.theme}</p>
          </div>
        )}
      </div>

      {/* Candidates */}
      <div className="space-y-4 mb-12">
        {digest.candidates.map((c, i) => (
          <div
            key={i}
            className="glass border border-white/[0.08] rounded-xl p-5 hover:border-white/20 transition-colors"
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                {c.icon && <span className="text-lg">{c.icon}</span>}
                <span className="text-xs font-mono text-white/40">#{c.rank || i + 1}</span>
                <span className={`text-sm font-bold ${relevanceColor(c.relevance)}`}>
                  {c.relevance}/5
                </span>
              </div>
              {c.cluster && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-white/40 whitespace-nowrap">
                  {c.cluster}
                </span>
              )}
            </div>

            <h3 className="text-base font-semibold text-white mb-2 leading-snug">{c.title}</h3>

            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-white/50 mb-3">
              {c.source && <span>{c.source}</span>}
              {c.published && <span>{c.published}</span>}
            </div>

            {c.summary && (
              <p className="text-sm text-white/80 leading-relaxed mb-3">{c.summary}</p>
            )}

            {c.url && (
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-cyan hover:text-white transition-colors"
              >
                View paper
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}
          </div>
        ))}
      </div>

      {/* Nav */}
      <div className="flex items-center justify-between border-t border-white/[0.08] pt-6">
        {prev ? (
          <Link to={`/digests/${prev.date}`} className="text-sm text-white/50 hover:text-cyan transition-colors">
            ← {prev.date}
          </Link>
        ) : <div />}
        {next ? (
          <Link to={`/digests/${next.date}`} className="text-sm text-white/50 hover:text-cyan transition-colors">
            {next.date} →
          </Link>
        ) : <div />}
      </div>
    </div>
  )
}
