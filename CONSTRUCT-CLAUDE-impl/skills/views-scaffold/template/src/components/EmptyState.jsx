import { Sparkles } from 'lucide-react'

// Per spec-v02-views.md §3.3. Friendly empty render with optional suggested action.
export default function EmptyState({ title = 'Nothing here yet', message, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl border border-white/10 bg-white/[0.04] mb-4">
        <Sparkles className="h-5 w-5 text-white/40" />
      </div>
      <h2 className="font-display text-lg text-white/80 mb-2">{title}</h2>
      {message && <p className="text-sm text-white/50 max-w-md leading-relaxed">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
