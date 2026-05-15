// Renders events from <workspace>/log/events.jsonl per data-model spec §5.6.
// Per spec-v02-views.md §4.4: format is `<time> <actor> <type> <subject>`.
export default function ActivityList({ events }) {
  if (!events || events.length === 0) {
    return <div className="text-sm text-white/40 italic">No recent activity.</div>
  }
  return (
    <ul className="divide-y divide-white/[0.04] border-y border-white/[0.04]">
      {events.map((e, i) => (
        <li key={`${e.timestamp}-${i}`} className="flex items-baseline gap-3 py-2 text-xs">
          <span className="text-white/30 tabular-nums shrink-0 w-32">{formatTime(e.timestamp)}</span>
          <span className="text-cyan-300/80 shrink-0 w-24">{e.actor || '—'}</span>
          <span className="text-white/60 shrink-0 w-32">{prettyType(e.type)}</span>
          <span className="text-white/80 truncate">{describeSubject(e)}</span>
        </li>
      ))}
    </ul>
  )
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d)) return iso
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`
  return d.toISOString().slice(0, 10)
}

function prettyType(type) {
  if (!type) return ''
  return type.replace(/_/g, ' ')
}

function describeSubject(event) {
  const s = event.subject || {}
  if (s.title) return s.title
  if (s.card_id) return s.card_id
  if (s.workspace) return s.workspace
  return event.skill || ''
}
