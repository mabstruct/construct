import { Link } from 'react-router-dom'

// Per spec-v02-views.md §4.4. Single big number + label.
// Optional `to` prop turns the tile into a navigation link.
export default function MetricTile({ value, label, sublabel, to, accent }) {
  const inner = (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors h-full">
      <div
        className="font-display text-3xl text-white tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      <div className="text-[10px] uppercase tracking-wider text-white/50 mt-1">
        {label}
      </div>
      {sublabel && (
        <div className="text-[10px] text-white/30 mt-2">{sublabel}</div>
      )}
    </div>
  )
  if (to) return <Link to={to} className="block focus:outline-none focus:ring-2 focus:ring-cyan-400/50 rounded-xl">{inner}</Link>
  return inner
}
