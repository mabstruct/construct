// Route: /:workspace/artifacts
// Spec: spec-v02-views.md §4.7
// Epic 8 implements: cards table, chip filters, side-panel detail via ?card=:id
import { useParams } from 'react-router-dom'

export default function Artifacts() {
  const { workspace } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Artifacts — /{workspace}/artifacts</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
