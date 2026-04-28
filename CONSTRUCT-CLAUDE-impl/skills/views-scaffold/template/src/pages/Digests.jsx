// Route: /:workspace/digests
// Spec: spec-v02-views.md §4.8
// Epic 8 implements: digest list rows, date-range filter
import { useParams } from 'react-router-dom'

export default function Digests() {
  const { workspace } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Digests — /{workspace}/digests</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
