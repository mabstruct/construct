// Route: /:workspace/knowledge-graph
// Spec: spec-v02-views.md §4.5
// Epic 8 implements: react-force-graph canvas, type+lifecycle filters, node side panel
import { useParams } from 'react-router-dom'

export default function KnowledgeGraph() {
  const { workspace } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Knowledge Graph — /{workspace}/knowledge-graph</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
