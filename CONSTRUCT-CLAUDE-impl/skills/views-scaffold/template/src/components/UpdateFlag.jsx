import { RefreshCw } from 'lucide-react'

// Per spec-v02-design-prototype.md §4.4 + spec-v02-views.md §5.1:
// invisible when fresh, cyan pill when stale, click reloads.
// Epic 8 wires `isStale` from useVersionFlag(). Epic 4 ships an unwired stub
// (default fresh; pass isStale={true} during prototype demos to see stale state).
export default function UpdateFlag({ isStale = false }) {
  if (!isStale) return null
  return (
    <button
      onClick={() => window.location.reload()}
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-cyan-300 border border-cyan-400/50 bg-cyan-400/5 hover:bg-cyan-400/10 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
      aria-label="Update available; reload page"
    >
      <RefreshCw className="h-3 w-3" />
      UPDATE
    </button>
  )
}
