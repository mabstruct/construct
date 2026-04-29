import { useEffect, useState } from 'react'

// Per spec-v02-views.md §3.4 + spec-v02-runtime-topology.md §4.
// Polls /version.json on mount + visibilitychange + every 30s while visible.
// First fetch establishes the loaded build_id; subsequent diffs flip isStale.
let loadedBuildId = null

export function useVersionFlag() {
  const [isStale, setIsStale] = useState(false)
  const [latestBuildId, setLatestBuildId] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const res = await fetch(`/version.json?t=${Date.now()}`, { cache: 'no-store' })
        if (!res.ok) return
        const ver = await res.json()
        if (cancelled) return
        if (loadedBuildId === null) {
          loadedBuildId = ver.build_id
        }
        setLatestBuildId(ver.build_id)
        if (ver.build_id !== loadedBuildId) setIsStale(true)
      } catch {
        // Network errors are silent — server might be down or transitioning.
      }
    }

    poll()

    function onVisibilityChange() {
      if (document.visibilityState === 'visible') poll()
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') poll()
    }, 30000)

    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisibilityChange)
      clearInterval(interval)
    }
  }, [])

  return {
    isStale,
    loadedBuildId,
    latestBuildId,
    reload: () => window.location.reload(),
  }
}
