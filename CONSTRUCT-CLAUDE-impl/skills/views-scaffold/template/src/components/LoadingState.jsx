// Per spec-v02-views.md §3.3. Skeleton placeholders matching final layout.
// `shape` prop hints which skeleton variant to render. Default = generic.
export default function LoadingState({ shape = 'generic' }) {
  if (shape === 'cards-table') {
    return (
      <div className="py-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-3 py-2 border-b border-white/[0.04] animate-pulse">
            <div className="h-4 w-1/3 rounded bg-white/[0.06]" />
            <div className="h-3 w-16 rounded bg-white/[0.04]" />
            <div className="h-3 w-12 rounded bg-white/[0.04]" />
            <div className="h-3 w-20 rounded bg-white/[0.04]" />
          </div>
        ))}
      </div>
    )
  }

  if (shape === 'dashboard') {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 animate-pulse">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl border border-white/[0.06] bg-white/[0.02]" />
        ))}
      </div>
    )
  }

  return (
    <div className="py-16 flex items-center justify-center animate-pulse">
      <div className="h-4 w-32 rounded bg-white/[0.06]" />
    </div>
  )
}
