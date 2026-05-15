import { useEffect, useState } from 'react'

// Per spec-v02-views.md §3.4. Module-scoped cache: persists for session,
// busts on full reload (the way fresh data lands per topology spec §4).
const cache = new Map()

export function useFetch(path, opts = {}) {
  const { meta = false } = opts
  const [state, setState] = useState(() => {
    const cached = cache.get(path)
    if (cached) {
      return {
        loading: false,
        data: meta ? cached.envelope : cached.envelope?.data ?? null,
        error: cached.error,
      }
    }
    return { loading: true, data: null, error: null }
  })

  useEffect(() => {
    if (cache.has(path)) return
    let active = true
    fetch(path)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${path}`)
        return res.json()
      })
      .then((envelope) => {
        cache.set(path, { envelope, error: null })
        if (active) {
          setState({
            loading: false,
            data: meta ? envelope : envelope?.data ?? null,
            error: null,
          })
        }
      })
      .catch((err) => {
        cache.set(path, { envelope: null, error: err })
        if (active) setState({ loading: false, data: null, error: err })
      })
    return () => {
      active = false
    }
  }, [path])

  return state
}
