// Route: /:workspace/digests/:id
// Spec: spec-v02-views.md §4.9
// Epic 8 implements: full-page digest with summary, top findings, search clusters
import { useParams } from 'react-router-dom'

export default function DigestDetail() {
  const { workspace, id } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Digest — /{workspace}/digests/{id}</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
