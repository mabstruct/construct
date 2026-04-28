import { NavLink } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

export default function Brand() {
  return (
    <NavLink to="/" className="group flex items-center gap-2.5 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 rounded-xl">
      <div className="relative grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/[0.06]">
        <Sparkles className="h-4 w-4 text-white/90" />
        <span className="absolute -inset-px rounded-xl bg-gradient-to-br from-fuchsia-500/20 via-cyan-400/10 to-indigo-500/20 opacity-0 blur-lg transition-opacity group-hover:opacity-100" />
      </div>
      <div className="leading-tight">
        <div className="font-display text-sm tracking-wide text-white font-semibold">MABSTRUCT</div>
        <div className="text-[10px] text-white/40 tracking-wider">CONSTRUCT</div>
      </div>
    </NavLink>
  )
}
