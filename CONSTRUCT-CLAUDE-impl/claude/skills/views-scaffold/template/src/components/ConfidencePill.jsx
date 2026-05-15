// 1–5 confidence visualised with the --confidence-N CSS vars.
export default function ConfidencePill({ value }) {
  const n = Number(value) || 0
  const clamped = Math.min(5, Math.max(0, Math.round(n)))
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium tabular-nums border"
      style={{
        color: `var(--confidence-${clamped || 1})`,
        borderColor: `var(--confidence-${clamped || 1})`,
        backgroundColor: 'rgba(255,255,255,0.02)',
        opacity: clamped === 0 ? 0.5 : 1,
      }}
      title={`Confidence ${clamped}/5`}
    >
      {clamped}/5
    </span>
  )
}
