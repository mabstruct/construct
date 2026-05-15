import { RefreshCw } from 'lucide-react'
import { useVersionFlag } from '../hooks/useVersionFlag'

// Per spec-v02-design-prototype.md §4.4 + spec-v02-views.md §5.1:
// invisible when fresh, cyan pill when stale, click reloads.
export default function UpdateFlag() {
  const { isStale, reload } = useVersionFlag()
  if (!isStale) return null
  return (
    <button
      onClick={reload}
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-cyan-300 border border-cyan-400/50 bg-cyan-400/5 hover:bg-cyan-400/10 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
      aria-label="Update available; reload page"
    >
      <RefreshCw className="h-3 w-3" />
      UPDATE
    </button>
  )
}
