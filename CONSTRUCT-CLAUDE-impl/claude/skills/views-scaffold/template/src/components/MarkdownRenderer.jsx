import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'

// Per spec-v02-views.md §5.3. Wraps react-markdown with theme-aware element
// overrides so prose looks right on the dark base. Used in CardSidePanel,
// ArticleDetail, DigestDetail.

// Internal paths get react-router Link (in-place client navigation, preserves
// scroll-to-anchor for `#card-id`); external schemes still open in a new tab.
function SmartLink({ href, children, ...rest }) {
  const isInternal = typeof href === 'string' && href.startsWith('/')
  const cls = 'text-cyan-300 hover:text-cyan-200 underline decoration-cyan-300/30 hover:decoration-cyan-200/60'
  if (isInternal) {
    return <Link to={href} className={cls} {...rest}>{children}</Link>
  }
  return <a href={href} className={cls} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>
}

const components = {
  h1: ({ node, ...p }) => <h1 className="font-display text-2xl text-white mt-6 mb-3 leading-tight" {...p} />,
  h2: ({ node, ...p }) => <h2 className="font-display text-xl text-white mt-6 mb-2 leading-snug" {...p} />,
  h3: ({ node, ...p }) => <h3 className="font-display text-lg text-white/90 mt-5 mb-2" {...p} />,
  h4: ({ node, ...p }) => <h4 className="font-display text-base text-white/80 mt-4 mb-2" {...p} />,
  p:  ({ node, ...p }) => <p className="my-3 leading-relaxed text-white/80" {...p} />,
  ul: ({ node, ...p }) => <ul className="my-3 ml-5 list-disc space-y-1 text-white/80" {...p} />,
  ol: ({ node, ...p }) => <ol className="my-3 ml-5 list-decimal space-y-1 text-white/80" {...p} />,
  li: ({ node, ...p }) => <li className="leading-relaxed" {...p} />,
  a:  ({ node, ...p }) => <SmartLink {...p} />,
  strong: ({ node, ...p }) => <strong className="text-white font-semibold" {...p} />,
  em: ({ node, ...p }) => <em className="italic text-white/85" {...p} />,
  code: ({ node, inline, className, ...p }) =>
    inline
      ? <code className="bg-white/[0.06] rounded px-1.5 py-0.5 text-cyan-200 font-mono text-[0.85em]" {...p} />
      : <code className={`block bg-transparent text-white/85 font-mono text-xs ${className || ''}`} {...p} />,
  pre: ({ node, ...p }) => <pre className="bg-white/[0.04] border border-white/[0.06] rounded-lg p-3 my-4 overflow-x-auto text-xs" {...p} />,
  blockquote: ({ node, ...p }) => <blockquote className="border-l-2 border-cyan-400/30 pl-4 my-4 italic text-white/60" {...p} />,
  hr: ({ node, ...p }) => <hr className="my-6 border-white/[0.08]" {...p} />,
  table: ({ node, ...p }) => <div className="my-4 overflow-x-auto"><table className="w-full border-collapse" {...p} /></div>,
  thead: ({ node, ...p }) => <thead className="bg-white/[0.04]" {...p} />,
  th: ({ node, ...p }) => <th className="px-3 py-2 text-left text-[10px] uppercase tracking-wider text-white/50 font-medium" {...p} />,
  td: ({ node, ...p }) => <td className="px-3 py-2 border-t border-white/[0.04] text-sm text-white/80" {...p} />,
  img: ({ node, ...p }) => <img className="max-w-full rounded my-3" {...p} />,
}

export default function MarkdownRenderer({ children }) {
  if (!children) return null
  return (
    <div className="markdown-body">
      <ReactMarkdown components={components}>{children}</ReactMarkdown>
    </div>
  )
}
