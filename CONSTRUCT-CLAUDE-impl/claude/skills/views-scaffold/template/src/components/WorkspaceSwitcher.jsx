import { useState, useRef, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronDown, Check } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'

// Per spec-v02-design-prototype.md §4.5 + spec-v02-views.md §5.2.
// Reads /data/domains.json — the user's actual workspaces appear in the dropdown.
export default function WorkspaceSwitcher() {
  const { workspace } = useParams()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const { data, loading, error } = useFetch('/data/domains.json')

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const workspaces = data?.domains || []
  const current = workspaces.find((w) => w.id === workspace)
  const label = current ? current.name : workspace || 'Switch workspace'

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-white/80 border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {label}
        <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute right-0 mt-2 w-64 rounded-lg border border-white/10 bg-black/80 backdrop-blur-xl shadow-lg overflow-hidden z-50"
        >
          {loading && (
            <div className="px-3 py-2 text-xs text-white/40">Loading…</div>
          )}
          {error && (
            <div className="px-3 py-2 text-xs text-amber-300">Could not load workspaces</div>
          )}
          {!loading && !error && workspaces.length === 0 && (
            <div className="px-3 py-2 text-xs text-white/40">No workspaces yet</div>
          )}
          {workspaces.map((w) => (
            <button
              key={w.id}
              role="option"
              aria-selected={w.id === workspace}
              onClick={() => {
                setOpen(false)
                navigate(`/${w.id}`)
              }}
              className="flex w-full items-center justify-between px-3 py-2 text-sm text-left text-white/80 hover:bg-white/[0.06]"
            >
              <span className="truncate">{w.name || w.id}</span>
              {w.id === workspace && <Check className="h-3.5 w-3.5 text-cyan-300 shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
