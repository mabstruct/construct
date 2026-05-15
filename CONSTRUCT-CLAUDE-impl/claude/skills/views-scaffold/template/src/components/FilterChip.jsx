import { useState, useRef, useEffect } from 'react'
import { ChevronDown, X } from 'lucide-react'

// Per spec-v02-views.md §3.2. Chip toolbar filter primitive.
// `mode = "multi"` → checklist popover (multi-select).
// `mode = "range"` → min/max number inputs popover.
// Active selection appears next to the chip as a small "Type: a, b ✕" badge.
export default function FilterChip({ label, mode = 'multi', options = [], value, onChange, min = 1, max = 5 }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const hasValue = mode === 'multi'
    ? Array.isArray(value) && value.length > 0
    : value && (value.min !== undefined || value.max !== undefined)

  const renderActive = () => {
    if (!hasValue) return null
    if (mode === 'multi') {
      const display = value.length <= 2 ? value.join(', ') : `${value.length} selected`
      return (
        <span className="ml-2 inline-flex items-center gap-1 text-cyan-300 text-[10px]">
          {display}
          <button
            onClick={(e) => { e.stopPropagation(); onChange([]) }}
            className="hover:text-white"
            aria-label="Clear filter"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      )
    }
    return (
      <span className="ml-2 inline-flex items-center gap-1 text-cyan-300 text-[10px]">
        {(value.min ?? min)}–{(value.max ?? max)}
        <button
          onClick={(e) => { e.stopPropagation(); onChange({}) }}
          className="hover:text-white"
        >
          <X className="h-3 w-3" />
        </button>
      </span>
    )
  }

  const triggerCls = `inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs border transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50 ${
    hasValue
      ? 'border-cyan-400/40 bg-cyan-400/5 text-white'
      : 'border-white/10 bg-white/[0.04] text-white/70 hover:bg-white/[0.08]'
  }`

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((o) => !o)} className={triggerCls} aria-expanded={open}>
        {label}
        {renderActive()}
        <ChevronDown className="h-3 w-3 ml-1" />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-2 w-56 rounded-lg border border-white/10 bg-black/90 backdrop-blur-xl shadow-lg z-40 p-2">
          {mode === 'multi' && (
            <ul className="max-h-64 overflow-y-auto">
              {options.map((opt) => {
                const sel = (value || []).includes(opt)
                return (
                  <li key={opt}>
                    <label className="flex items-center gap-2 px-2 py-1.5 text-sm text-white/80 hover:bg-white/[0.06] rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={sel}
                        onChange={() => {
                          const cur = value || []
                          onChange(sel ? cur.filter((v) => v !== opt) : [...cur, opt])
                        }}
                        className="accent-cyan-400"
                      />
                      <span className="capitalize">{opt}</span>
                    </label>
                  </li>
                )
              })}
            </ul>
          )}
          {mode === 'range' && (
            <div className="px-2 py-1 space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-[10px] uppercase tracking-wider text-white/40 w-10">min</label>
                <input
                  type="number"
                  min={min}
                  max={max}
                  value={value?.min ?? ''}
                  onChange={(e) => onChange({ ...(value || {}), min: e.target.value === '' ? undefined : Number(e.target.value) })}
                  className="w-full bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-sm text-white"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-[10px] uppercase tracking-wider text-white/40 w-10">max</label>
                <input
                  type="number"
                  min={min}
                  max={max}
                  value={value?.max ?? ''}
                  onChange={(e) => onChange({ ...(value || {}), max: e.target.value === '' ? undefined : Number(e.target.value) })}
                  className="w-full bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-sm text-white"
                />
              </div>
              <div className="text-[10px] text-white/30 pt-1">Range {min}–{max}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
