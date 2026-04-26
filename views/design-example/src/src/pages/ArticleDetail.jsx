import { useParams, Link } from 'react-router-dom'
import Markdown from 'react-markdown'
import articles from '../data/articles.json'

const registerColors = {
  research: 'text-cyan',
  reflection: 'text-violet',
  constructing: 'text-orange',
  inference: 'text-emerald',
}

const domainLabels = {
  math: 'Mathematics',
  ai: 'AI & Agents',
  awareness: 'Awareness',
  cosmology: 'Cosmology',
}

export default function ArticleDetail() {
  const { id } = useParams()
  const article = articles.find(a => a.id === id)

  if (!article) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-20 text-center">
        <h1 className="text-2xl font-display font-bold text-white mb-4">Article not found</h1>
        <Link to="/thought-stream" className="text-white/40 hover:text-white/80 transition-colors">Back to Thought Stream</Link>
      </div>
    )
  }

  const idx = articles.findIndex(a => a.id === id)
  const prev = idx < articles.length - 1 ? articles[idx + 1] : null
  const next = idx > 0 ? articles[idx - 1] : null

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-white/40 mb-8">
        <Link to="/thought-stream" className="text-white/40 hover:text-white/80 transition-colors">Thought Stream</Link>
        <span className="text-white/20">/</span>
        <span className="text-white/80 truncate">{article.title}</span>
      </div>

      {/* Meta */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-sm font-mono text-white/50">{article.date}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${registerColors[article.register] || 'text-white/40'}`} style={{
          borderColor: `rgba(255, 255, 255, 0.1)`,
          backgroundColor: `rgba(255, 255, 255, 0.05)`
        }}>
          {article.register}
        </span>
        {article.domains.map(d => (
          <span key={d} className="text-xs px-2 py-0.5 rounded-full border text-white/40" style={{
            borderColor: `rgba(255, 255, 255, 0.1)`,
            backgroundColor: `rgba(255, 255, 255, 0.05)`
          }}>
            {domainLabels[d] || d}
          </span>
        ))}
        {article.certainty && (
          <span className="text-xs text-white/40">
            certainty: {article.certainty}/5
          </span>
        )}
      </div>

      {/* Summary */}
      {article.summary && (
        <div className="glass rounded-lg p-4 mb-8 border border-white/[0.08]">
          <p className="text-sm text-white/60 leading-relaxed italic">{article.summary}</p>
        </div>
      )}

      {/* Content */}
      <article className="prose-dark">
        <Markdown>{article.content}</Markdown>
      </article>

      {/* Nav */}
      <div className="flex items-center justify-between border-t border-white/[0.06] pt-8 mt-12">
        {prev ? (
          <Link to={`/thought-stream/${prev.id}`} className="group max-w-[45%]">
            <div className="text-xs text-white/40 mb-1">Previous</div>
            <div className="text-sm text-white/40 group-hover:text-white/80 transition-colors truncate">
              ← {prev.title}
            </div>
          </Link>
        ) : <div />}
        {next ? (
          <Link to={`/thought-stream/${next.id}`} className="group max-w-[45%] text-right">
            <div className="text-xs text-white/40 mb-1">Next</div>
            <div className="text-sm text-white/40 group-hover:text-white/80 transition-colors truncate">
              {next.title} →
            </div>
          </Link>
        ) : <div />}
      </div>
    </div>
  )
}
