// Route: * (catch-all)
// Spec: spec-v02-views.md §4.10
// Renders for any unmatched URL. Always succeeds — no fetch, no errors.
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="p-8">
      <h1 className="text-2xl">Page not found</h1>
      <p className="opacity-60 mt-2">
        <Link to="/" className="underline">Back to landing</Link>
      </p>
    </div>
  )
}
