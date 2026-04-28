// Route: /articles/:slug
// Spec: spec-v02-views.md §4.3
// Epic 8 implements: full-page article + provenance trace
import { useParams } from 'react-router-dom'

export default function ArticleDetail() {
  const { slug } = useParams()
  return (
    <div className="p-8">
      <h1 className="text-2xl">Article — /articles/{slug}</h1>
      <p className="opacity-60 mt-2">Epic 8 implements this view.</p>
    </div>
  )
}
