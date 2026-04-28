// Route: /:workspace/
// Spec: spec-v02-views.md §4.4
// Epic 8 implements: per-workspace metrics, charts, activity feed
import { useParams } from 'react-router-dom'

export default function WorkspaceDashboard() {
  const { workspace } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Workspace Dashboard — /{workspace}/</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
