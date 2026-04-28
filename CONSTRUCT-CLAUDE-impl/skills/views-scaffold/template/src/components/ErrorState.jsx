import { AlertTriangle } from 'lucide-react'

// Per spec-v02-views.md §3.3. Failure render with retry button.
export default function ErrorState({ message = 'Something went wrong loading this view.', retry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl border border-amber-400/30 bg-amber-400/5 mb-4">
        <AlertTriangle className="h-5 w-5 text-amber-300" />
      </div>
      <h2 className="font-display text-lg text-white/80 mb-2">Could not load</h2>
      <p className="text-sm text-white/50 max-w-md leading-relaxed">{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="mt-4 rounded-lg px-4 py-2 text-sm border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
        >
          Retry
        </button>
      )}
    </div>
  )
}
