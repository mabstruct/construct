import { Routes, Route } from 'react-router-dom'

import Landing from './pages/Landing'
import Articles from './pages/Articles'
import ArticleDetail from './pages/ArticleDetail'
import WorkspaceDashboard from './pages/WorkspaceDashboard'
import KnowledgeGraph from './pages/KnowledgeGraph'
import Landscape from './pages/Landscape'
import Artifacts from './pages/Artifacts'
import Digests from './pages/Digests'
import DigestDetail from './pages/DigestDetail'
import NotFound from './pages/NotFound'

// Route map mirrors spec-v02-runtime-topology.md §5.
// Cross-workspace routes at root; per-workspace routes under /:workspace/.
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/articles" element={<Articles />} />
      <Route path="/articles/:slug" element={<ArticleDetail />} />
      <Route path="/:workspace" element={<WorkspaceDashboard />} />
      <Route path="/:workspace/knowledge-graph" element={<KnowledgeGraph />} />
      <Route path="/:workspace/landscape" element={<Landscape />} />
      <Route path="/:workspace/artifacts" element={<Artifacts />} />
      <Route path="/:workspace/digests" element={<Digests />} />
      <Route path="/:workspace/digests/:id" element={<DigestDetail />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
