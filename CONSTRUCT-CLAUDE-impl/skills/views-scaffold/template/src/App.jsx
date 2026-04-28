import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './routes'

// Epic 4 will wrap <AppRoutes/> in a <Layout> component (Header, CosmicBG, Footer).
// Epic 3 ships with the bare router so the route shell can be tested end-to-end.
export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
