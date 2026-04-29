// Compact 1–5 source-tier indicator. Lower number = higher tier (better source).
export default function SourceTierIndicator({ value }) {
  const n = Number(value) || 0
  const clamped = Math.min(5, Math.max(1, n || 5))
  return (
    <span
      className="inline-flex items-center text-[10px] tabular-nums text-white/60"
      title={`Source tier ${clamped}/5 (1 = strongest)`}
    >
      T{clamped}
    </span>
  )
}
