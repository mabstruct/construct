import { Link, useParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import MarkdownRenderer from '../components/MarkdownRenderer'
import Tag from '../components/Tag'
import ConfidencePill from '../components/ConfidencePill'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'

// Route: /articles/:slug
// Spec: spec-v02-views.md §4.3
export default function ArticleDetail() {
  const { slug } = useParams()
  const { data, loading, error } = useFetch('/data/articles.json')

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />

  const article = (data?.articles || []).find((a) => a.id === slug)
  if (!article) {
    return (
      <div className="py-8">
        <h1 className="font-display text-2xl text-white mb-2">Article not found</h1>
        <p className="text-sm text-white/50">
          No article with id <code className="text-cyan-300">{slug}</code> in this build.
        </p>
        <Link to="/articles" className="text-xs text-cyan-300 hover:text-cyan-200 mt-4 inline-block">
          ← Back to articles
        </Link>
      </div>
    )
  }

  return (
    <article className="py-8 space-y-8 max-w-3xl mx-auto">
      <header className="space-y-3 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-white/40">
          {article.type && <span>{article.type}</span>}
          {article.status && (
            <>
              <span className="text-white/20">·</span>
              <span className={article.status === 'published' ? 'text-cyan-300' : 'text-amber-300'}>
                {article.status}
              </span>
            </>
          )}
          {article.date && (
            <>
              <span className="text-white/20">·</span>
              <span>{article.date}</span>
            </>
          )}
        </div>
        <h1 className="font-display text-3xl md:text-4xl text-white leading-tight tracking-tight">
          {article.title}
        </h1>
        <div className="flex items-center gap-2 flex-wrap text-xs text-white/50">
          {(article.workspaces || []).map((w) => (
            <Link key={w} to={`/${w}`} className="hover:text-white">
              {w}
            </Link>
          ))}
          {typeof article.confidence_floor === 'number' && article.confidence_floor > 0 && (
            <>
              <span className="text-white/20">·</span>
              <span>confidence floor ≥ {article.confidence_floor}</span>
            </>
          )}
        </div>
      </header>

      {article.body_markdown && (
        <div className="text-base leading-relaxed">
          <MarkdownRenderer>{article.body_markdown}</MarkdownRenderer>
        </div>
      )}

      {article.source_cards && article.source_cards.length > 0 && (
        <section className="border-t border-white/[0.04] pt-6">
          <h2 className="font-display text-xl text-white/80 mb-4">Sources</h2>
          <ul className="divide-y divide-white/[0.04] border-y border-white/[0.04]">
            {article.source_cards.map((s, i) => (
              <SourceRow key={s.id || i} source={s} />
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}

function SourceRow({ source }) {
  const isMissing = source.status === 'missing'
  if (isMissing) {
    return (
      <li className="py-3 px-2 text-xs text-white/30 italic">
        <span className="line-through">{source.id}</span>{' '}
        <span className="text-amber-400/60 not-italic">(card removed)</span>
      </li>
    )
  }
  return (
    <li className="py-3 px-2">
      <Link
        to={`/${source.workspace_id}/artifacts?card=${source.id}`}
        className="block hover:bg-white/[0.02] -mx-2 px-2 rounded transition-colors"
      >
        <div className="flex items-center gap-3 text-sm">
          <Tag tone="type">{source.epistemic_type}</Tag>
          <ConfidencePill value={source.confidence} />
          <span className="text-white/85 truncate flex-1">{source.title}</span>
          <span className="text-[10px] text-white/30 hidden md:inline">{source.workspace_id}</span>
        </div>
        {source.contribution && (
          <div className="text-xs text-white/50 mt-1.5 ml-1 leading-relaxed">
            {source.contribution}
          </div>
        )}
      </Link>
    </li>
  )
}
