import { NavLink, Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Sparkles, Home, Radio, BookOpen, Layers, Cpu, Map, GitBranch } from 'lucide-react'

const links = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/thought-stream', label: 'Thought Stream', icon: Radio },
  { to: '/digests', label: 'Digests', icon: BookOpen },
  { to: '/analysis', label: 'ISW Analysis', icon: Layers },
  { to: '/landscape', label: 'ISW Landscape', icon: Map },
  { to: '/knowledge-graph', label: 'Knowledge Graph', icon: GitBranch },
  { to: '/architecture', label: 'Architecture', icon: Cpu },
]

function CosmicBG() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden z-0">
      <div className="absolute -inset-[30%] bg-[radial-gradient(circle_at_20%_20%,rgba(168,85,247,0.18),transparent_45%),radial-gradient(circle_at_80%_30%,rgba(34,211,238,0.12),transparent_45%),radial-gradient(circle_at_40%_85%,rgba(99,102,241,0.14),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,rgba(0,0,0,0.8)_85%)]" />
      <div className="absolute inset-0 opacity-25 bg-[radial-gradient(1px_1px_at_10%_20%,rgba(255,255,255,0.9),transparent_60%),radial-gradient(1px_1px_at_30%_70%,rgba(255,255,255,0.8),transparent_60%),radial-gradient(1px_1px_at_70%_30%,rgba(255,255,255,0.7),transparent_60%),radial-gradient(1px_1px_at_85%_65%,rgba(255,255,255,0.8),transparent_60%),radial-gradient(1px_1px_at_55%_45%,rgba(255,255,255,0.65),transparent_60%)]" />
      <div className="absolute left-1/2 top-[40%] h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.04] animate-[spin_120s_linear_infinite]" />
      <div className="absolute left-1/2 top-[40%] h-[560px] w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.06] animate-[spin_90s_linear_infinite_reverse]" />
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)

  // Load fonts
  useEffect(() => {
    if (typeof document === 'undefined') return
    const id = 'mabstruct-fonts'
    if (!document.getElementById(id)) {
      const link = document.createElement('link')
      link.id = id
      link.rel = 'stylesheet'
      link.href = 'https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Manrope:wght@300;400;500;600&display=swap'
      document.head.appendChild(link)
    }
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      <CosmicBG />

      {/* Header — glass nav */}
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-black/40 backdrop-blur-2xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <NavLink to="/" className="group flex items-center gap-2.5">
              <div className="relative grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/[0.06]">
                <Sparkles className="h-4 w-4 text-white/90" />
                <span className="absolute -inset-px rounded-xl bg-gradient-to-br from-fuchsia-500/20 via-cyan-400/10 to-indigo-500/20 opacity-0 blur-lg transition-opacity group-hover:opacity-100" />
              </div>
              <div className="leading-tight">
                <div className="font-display text-sm tracking-wide text-white font-semibold">MABSTRUCT</div>
                <div className="text-[10px] text-white/40 tracking-wider">CONSTRUCT</div>
              </div>
            </NavLink>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-1">
              {links.map(l => {
                const Icon = l.icon
                return (
                  <NavLink
                    key={l.to}
                    to={l.to}
                    end={l.to === '/'}
                    className={({ isActive }) =>
                      `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-all ${
                        isActive
                          ? 'bg-white/[0.1] text-white'
                          : 'text-white/50 hover:text-white/80 hover:bg-white/[0.05]'
                      }`
                    }
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {l.label}
                  </NavLink>
                )
              })}
            </nav>

            {/* Mobile toggle */}
            <button
              onClick={() => setOpen(!open)}
              className="md:hidden p-2 text-white/50 hover:text-white"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {open
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                }
              </svg>
            </button>
          </div>

          {/* Mobile nav */}
          {open && (
            <nav className="md:hidden pb-4 flex flex-col gap-1">
              {links.map(l => {
                const Icon = l.icon
                return (
                  <NavLink
                    key={l.to}
                    to={l.to}
                    end={l.to === '/'}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${
                        isActive ? 'bg-white/[0.1] text-white' : 'text-white/50 hover:text-white/80'
                      }`
                    }
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {l.label}
                  </NavLink>
                )
              })}
            </nav>
          )}
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 relative z-10 px-6 md:px-10 lg:px-12">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/[0.05] mt-10">
        <div className="max-w-6xl mx-auto py-8 flex flex-col md:flex-row items-center justify-between gap-4 px-6">
          <div>
            <span className="font-display text-white/60 text-sm">MABSTRUCT</span>
            <span className="text-white/20 text-xs ml-3">CONSTRUCT — autonomous agentic research engine</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[10px] text-white/15">Research data updated daily via OpenClaw</span>
            <span className="text-[10px] text-white/15">© {new Date().getFullYear()}</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
