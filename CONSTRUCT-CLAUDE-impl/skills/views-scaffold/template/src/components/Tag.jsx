// Small pill for epistemic_type, content_categories, tags etc.
// `tone` picks a colour ramp keyed on lifecycle / confidence semantics.
export default function Tag({ children, tone = 'neutral' }) {
  const tones = {
    neutral:    'border-white/10 bg-white/[0.04] text-white/70',
    type:       'border-cyan-400/30 bg-cyan-400/5 text-cyan-200',
    lifecycle_seed:     'border-indigo-400/30 bg-indigo-400/5 text-indigo-200',
    lifecycle_growing:  'border-cyan-400/30 bg-cyan-400/5 text-cyan-200',
    lifecycle_mature:   'border-emerald-400/30 bg-emerald-400/5 text-emerald-200',
    lifecycle_archived: 'border-white/15 bg-white/[0.02] text-white/40',
  }
  const cls = tones[tone] || tones.neutral
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide whitespace-nowrap ${cls}`}>
      {children}
    </span>
  )
}
