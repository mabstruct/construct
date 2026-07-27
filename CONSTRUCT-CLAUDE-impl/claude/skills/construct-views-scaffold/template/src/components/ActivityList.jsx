// Renders events from <workspace>/log/events.jsonl per data-model spec §5.6.
//
// D-17: the canonical event shape is the one the Python emitter writes
// (construct/services/event_log.py via schemas/config.py EventRecord) and the one
// views/lib/parse_events.py now canonicalises every log line into:
// ts, agent, action, target, detail, result.
//
// This component used to read five keys that no emitter in CONSTRUCT has ever
// produced — a legacy timestamp key, an actor key, a kind key, a nested
// what-was-acted-on object, and a skill key. The nested object existed in no
// emitter at all. Every Python-emitted event therefore rendered here with a
// blank actor and a blank action. That was a live defect before the contract
// work, not a regression from it; conforming the reader to the writer is the fix
// (research Finding V3/V5).
//
// `result` is rendered, not just read. An escalated action wrote nothing by
// design, and an activity list that draws it identically to an applied change is
// the audit-trail-that-lies defect wearing a browser.
//
// Row format per spec-v02-views.md §4.4: `<time> <agent> <action> <what>`, plus
// the outcome badge when the outcome was not a plain success.
export default function ActivityList({ events }) {
  if (!events || events.length === 0) {
    return <div className="text-sm text-white/40 italic">No recent activity.</div>
  }
  return (
    <ul className="divide-y divide-white/[0.04] border-y border-white/[0.04]">
      {events.map((e, i) => (
        <li key={`${e.ts}-${i}`} className="flex items-baseline gap-3 py-2 text-xs">
          <span className="text-white/30 tabular-nums shrink-0 w-32">{formatTime(e.ts)}</span>
          <span className="text-cyan-300/80 shrink-0 w-24">{e.agent || '—'}</span>
          <span className="text-white/60 shrink-0 w-32">{prettyType(e.action)}</span>
          <span className="text-white/80 truncate">{describeTarget(e)}</span>
          <ResultBadge result={e.result} />
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

// The canonical shape carries no nested object and no pre-composed description:
// `target` names what was acted on and `detail` is free text about it. Both are
// optional, so every combination has to read sensibly on its own.
function describeTarget(e) {
  const what = e.target || ''
  const why = e.detail || ''
  if (what && why) return `${what} — ${why}`
  return what || why
}

// `success` is the overwhelming majority and needs no decoration; anything else
// is the case a reader must not miss.
const RESULT_STYLES = {
  failure: 'text-rose-300/90 border-rose-400/20 bg-rose-500/10',
  escalated: 'text-amber-300/90 border-amber-400/20 bg-amber-500/10',
}

function ResultBadge({ result }) {
  // `result` comes out of a JSON file, so it can be any string — including one
  // that names something on Object.prototype. The typeof check keeps a
  // `constructor` or `__proto__` value from resolving to an inherited member and
  // being interpolated into className.
  const style = RESULT_STYLES[result]
  if (typeof style !== 'string') return null
  return (
    <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${style}`}>
      {result}
    </span>
  )
}
