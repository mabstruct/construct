// Atmospheric background per spec-v02-design-prototype.md §3.4.
// 3 layers (gradients + vignette + stars) consuming CSS custom properties so
// per-workspace overrides via [data-workspace="..."] work without component changes.
// No rotating rings (removed for v0.2 — distracting on a working tool).
export default function CosmicBG() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden z-0">
      {/* Layer 1: corner radial-gradient washes */}
      <div
        className="absolute -inset-[30%]"
        style={{
          background: `
            radial-gradient(circle at 20% 20%, var(--cosmic-grad-a), transparent 45%),
            radial-gradient(circle at 80% 30%, var(--cosmic-grad-b), transparent 45%),
            radial-gradient(circle at 40% 85%, var(--cosmic-grad-c), transparent 50%)
          `,
        }}
      />
      {/* Layer 2: dark vignette for content legibility */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(circle at center, transparent 30%, rgba(0,0,0,0.8) 85%)',
        }}
      />
      {/* Layer 3: 5 fixed star particles */}
      <div
        className="absolute inset-0"
        style={{
          opacity: 'var(--star-opacity)',
          background: `
            radial-gradient(1px 1px at 10% 20%, rgba(255,255,255,0.9), transparent 60%),
            radial-gradient(1px 1px at 30% 70%, rgba(255,255,255,0.8), transparent 60%),
            radial-gradient(1px 1px at 70% 30%, rgba(255,255,255,0.7), transparent 60%),
            radial-gradient(1px 1px at 85% 65%, rgba(255,255,255,0.8), transparent 60%),
            radial-gradient(1px 1px at 55% 45%, rgba(255,255,255,0.65), transparent 60%)
          `,
        }}
      />
    </div>
  )
}
