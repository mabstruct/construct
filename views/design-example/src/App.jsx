import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Blog from './pages/Blog'
import ArticleDetail from './pages/ArticleDetail'
import Digests from './pages/Digests'
import DigestDetail from './pages/DigestDetail'
import Analysis from './pages/Analysis'
import Architecture from './pages/Architecture'
import Landscape from './pages/Landscape'
import KnowledgeGraph from './pages/KnowledgeGraph'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="thought-stream" element={<Blog />} />
        <Route path="thought-stream/:id" element={<ArticleDetail />} />
        <Route path="digests" element={<Digests />} />
        <Route path="digests/:date" element={<DigestDetail />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="landscape" element={<Landscape />} />
        <Route path="knowledge-graph" element={<KnowledgeGraph />} />
        <Route path="architecture" element={<Architecture />} />
      </Route>
    </Routes>
  )
}
