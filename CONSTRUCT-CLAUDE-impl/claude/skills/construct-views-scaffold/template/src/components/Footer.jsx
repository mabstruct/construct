// Per spec-v02-design-prototype.md §4.6.
// Brand + version + generation timestamp + install path. No OpenClaw reference.
// Epic 8 wires real values from version.json + domains.json envelope.
export default function Footer({ version, generatedAt, installPath } = {}) {
  return (
    <footer className="relative z-10 border-t border-white/[0.05] mt-10">
      <div className="max-w-6xl mx-auto py-6 flex flex-col md:flex-row items-center justify-between gap-3 px-6">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-white/60 text-sm tracking-wide">MABSTRUCT</span>
          <span className="text-[10px] text-white/30 tracking-wider">CONSTRUCT</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-white/30">
          {version && <span>v{version}</span>}
          {generatedAt && <span>generated {generatedAt}</span>}
          {installPath && <span className="truncate max-w-xs">{installPath}</span>}
        </div>
      </div>
    </footer>
  )
}
