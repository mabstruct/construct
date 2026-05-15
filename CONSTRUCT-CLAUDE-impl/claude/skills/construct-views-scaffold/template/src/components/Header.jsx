import { NavLink, useParams } from 'react-router-dom'
import Brand from './Brand'
import WorkspaceSwitcher from './WorkspaceSwitcher'
import UpdateFlag from './UpdateFlag'

// Per spec-v02-design-prototype.md §4.1.
// Two-row sticky header. Top always; bottom only on /<workspace>/* routes.
// Wiki added per spec-v02-knowledge-views-spike.md §3.6 (Slice 12.1, locked
// 2026-05-02). Placed adjacent to Artifacts since they share the card-data
// surface; Wiki is the reading view, Artifacts is the filtered index.
const WORKSPACE_LINKS = [
  { to: '', label: 'Dashboard' },
  { to: '/knowledge-graph', label: 'Knowledge Graph' },
  { to: '/landscape', label: 'Landscape' },
  { to: '/artifacts', label: 'Artifacts' },
  { to: '/wiki', label: 'Wiki' },
  { to: '/digests', label: 'Digests' },
]

export default function Header() {
  const { workspace } = useParams()

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-black/40 backdrop-blur-2xl">
      {/* Top row — always visible */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <Brand />
          <nav className="hidden md:flex items-center gap-3">
            <NavLink
              to="/articles"
              className={({ isActive }) =>
                `text-sm transition-colors ${isActive ? 'text-white' : 'text-white/60 hover:text-white/90'}`
              }
            >
              Articles
            </NavLink>
          </nav>
          <div className="flex items-center gap-3">
            <UpdateFlag />
            <WorkspaceSwitcher />
          </div>
        </div>
      </div>

      {/* Bottom row — only on /<workspace>/... routes */}
      {workspace && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 border-t border-white/[0.04]">
          <nav className="flex items-center gap-1 h-11 overflow-x-auto">
            {WORKSPACE_LINKS.map((l) => (
              <NavLink
                key={l.to || 'dashboard'}
                to={`/${workspace}${l.to}`}
                end={l.to === ''}
                className={({ isActive }) =>
                  `flex items-center rounded-lg px-3 py-1.5 text-sm whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-white/[0.1] text-white'
                      : 'text-white/50 hover:text-white/80 hover:bg-white/[0.05]'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      )}
    </header>
  )
}
