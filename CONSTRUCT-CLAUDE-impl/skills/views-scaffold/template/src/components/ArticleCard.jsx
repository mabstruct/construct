import { Link } from 'react-router-dom'

// Per spec-v02-views.md §4.2: magazine-style card. Used in Landing strip
// and (later, Slice 3) the Articles list.
export default function ArticleCard({ article }) {
  const ws = (article.workspaces || []).join(', ')
  return (
    <Link
      to={`/articles/${article.id}`}
      className="block rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
    >
      <h4 className="font-display text-base text-white line-clamp-2 leading-snug">
        {article.title}
      </h4>
      {article.excerpt && (
        <p className="text-xs text-white/50 mt-2 line-clamp-3 leading-relaxed">
          {article.excerpt}
        </p>
      )}
      <div className="flex items-center gap-2 mt-3 text-[10px] text-white/30 uppercase tracking-wider flex-wrap">
        {article.type && <span>{article.type}</span>}
        {article.date && (
          <>
            <span className="text-white/15">·</span>
            <span>{article.date}</span>
          </>
        )}
        {ws && (
          <>
            <span className="text-white/15">·</span>
            <span className="normal-case tracking-normal">{ws}</span>
          </>
        )}
      </div>
    </Link>
  )
}
