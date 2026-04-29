import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import MarkdownRenderer from './MarkdownRenderer'
import Tag from './Tag'
import ConfidencePill from './ConfidencePill'
import SourceTierIndicator from './SourceTierIndicator'

// Per spec-v02-views.md §4.7. Side panel rendered when ?card=:id in URL.
// Receives the card object + the connection list for the workspace +
// a callback for the close (X) and connection-jump (?card=other).
export default function CardSidePanel({ card, connections, workspace, onClose, onSelect }) {
  if (!card) return null

  const inbound = connections.filter((c) => c.target === card.id)
  const outbound = connections.filter((c) => c.source === card.id)

  return (
    <aside className="fixed top-14 md:top-[6.5rem] right-0 bottom-0 w-full md:w-[480px] z-40 border-l border-white/[0.06] bg-black/90 backdrop-blur-xl overflow-y-auto">
      <div className="sticky top-0 flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-black/60 backdrop-blur-xl">
        <span className="font-display text-xs uppercase tracking-wider text-white/50">Card</span>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-white/[0.06] focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          aria-label="Close detail"
        >
          <X className="h-4 w-4 text-white/60" />
        </button>
      </div>

      <div className="px-5 py-5 space-y-5">
        <div>
          <h2 className="font-display text-xl text-white leading-snug">{card.title}</h2>
          <div className="text-[10px] text-white/30 mt-1">{card.id}</div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Tag tone="type">{card.epistemic_type}</Tag>
          <Tag tone={`lifecycle_${card.lifecycle}`}>{card.lifecycle}</Tag>
          <ConfidencePill value={card.confidence} />
          <SourceTierIndicator value={card.source_tier} />
        </div>

        {card.tags && card.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {card.tags.map((t) => <Tag key={t}>{t}</Tag>)}
          </div>
        )}

        <div className="text-xs text-white/50 space-y-1">
          {card.author && <div>author: <span className="text-white/70">{card.author}</span></div>}
          {card.created && <div>created: <span className="text-white/70 tabular-nums">{card.created}</span></div>}
          {card.last_reviewed && <div>last reviewed: <span className="text-white/70 tabular-nums">{card.last_reviewed}</span></div>}
        </div>

        {card.body_markdown && (
          <div className="text-sm">
            <MarkdownRenderer>{card.body_markdown}</MarkdownRenderer>
          </div>
        )}

        {card.sources && card.sources.length > 0 && (
          <div className="border-t border-white/[0.04] pt-4">
            <h3 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">Sources</h3>
            <ul className="space-y-1.5 text-xs">
              {card.sources.map((s, i) => (
                <li key={i} className="text-white/70">
                  {s.ref ? (
                    <a href={s.ref} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:text-cyan-200 underline">
                      {s.title || s.ref}
                    </a>
                  ) : (
                    s.title || JSON.stringify(s)
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {(inbound.length > 0 || outbound.length > 0) && (
          <div className="border-t border-white/[0.04] pt-4">
            <h3 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">
              Connections ({inbound.length + outbound.length})
            </h3>
            <ul className="space-y-1 text-xs">
              {outbound.map((c) => (
                <li key={c.id} className="flex items-center gap-2">
                  <Tag>{c.type}</Tag>
                  <span className="text-white/40">→</span>
                  <button
                    onClick={() => onSelect(c.target)}
                    className="text-cyan-300 hover:text-cyan-200 truncate"
                  >
                    {c.target}
                  </button>
                </li>
              ))}
              {inbound.map((c) => (
                <li key={c.id} className="flex items-center gap-2">
                  <Tag>{c.type}</Tag>
                  <span className="text-white/40">←</span>
                  <button
                    onClick={() => onSelect(c.source)}
                    className="text-cyan-300 hover:text-cyan-200 truncate"
                  >
                    {c.source}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </aside>
  )
}
