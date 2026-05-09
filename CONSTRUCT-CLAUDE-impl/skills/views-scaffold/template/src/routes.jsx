import { Routes, Route, Navigate, useParams } from 'react-router-dom'

import Landing from './pages/Landing'
import Articles from './pages/Articles'
import ArticleDetail from './pages/ArticleDetail'
import WorkspaceDashboard from './pages/WorkspaceDashboard'
import KnowledgeGraph from './pages/KnowledgeGraph'
import Landscape from './pages/Landscape'
import Artifacts from './pages/Artifacts'
import Digests from './pages/Digests'
import DigestDetail from './pages/DigestDetail'
import Wiki from './pages/Wiki'
import NotFound from './pages/NotFound'
import useFetch from './hooks/useFetch'

// Reads workspace_landing from domains.json settings and redirects
// to wiki if configured, otherwise renders the default dashboard.
function WorkspaceEntry() {
  const { workspace } = useParams()
  const { data } = useFetch('/data/domains.json')
  const landing = data?.settings?.workspace_landing

  if (landing === 'wiki') {
    return <Navigate to={`/${workspace}/wiki`} replace />
  }
  return <WorkspaceDashboard />
}

// Route map mirrors spec-v02-runtime-topology.md §5.
// Cross-workspace routes at root; per-workspace routes under /:workspace/.
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/articles" element={<Articles />} />
      <Route path="/articles/:slug" element={<ArticleDetail />} />
      <Route path="/:workspace" element={<WorkspaceEntry />} />
      <Route path="/:workspace/knowledge-graph" element={<KnowledgeGraph />} />
      <Route path="/:workspace/landscape" element={<Landscape />} />
      <Route path="/:workspace/artifacts" element={<Artifacts />} />
      <Route path="/:workspace/wiki" element={<Wiki />} />
      <Route path="/:workspace/digests" element={<Digests />} />
      <Route path="/:workspace/digests/:id" element={<DigestDetail />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
