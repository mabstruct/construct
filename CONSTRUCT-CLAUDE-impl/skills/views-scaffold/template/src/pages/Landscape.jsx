// Route: /:workspace/landscape
// Spec: spec-v02-views.md §4.6
// Epic 8 implements: domain health metrics, taxonomy heatmap
import { useParams } from 'react-router-dom'

export default function Landscape() {
  const { workspace } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Landscape — /{workspace}/landscape</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
