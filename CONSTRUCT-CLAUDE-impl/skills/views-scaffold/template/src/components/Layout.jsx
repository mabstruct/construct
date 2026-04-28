import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import CosmicBG from './CosmicBG'
import Header from './Header'
import Footer from './Footer'

// Layout wraps every route. data-workspace attribute prepares per-workspace
// theme overrides for v0.2.1+ (substrate noted in spec-v02-design-prototype §3.5).
export default function Layout({ children }) {
  const { workspace } = useParams()

  // Load Syne + Manrope from Google Fonts once per session
  useEffect(() => {
    const id = 'construct-fonts'
    if (typeof document === 'undefined' || document.getElementById(id)) return
    const link = document.createElement('link')
    link.id = id
    link.rel = 'stylesheet'
    link.href =
      'https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Manrope:wght@300;400;500;600&display=swap'
    document.head.appendChild(link)
  }, [])

  return (
    <div data-workspace={workspace || 'default'} className="min-h-screen flex flex-col">
      <CosmicBG />
      <Header />
      <main className="flex-1 relative z-10 px-6 md:px-10 lg:px-12 max-w-6xl mx-auto w-full">
        {children}
      </main>
      <Footer />
    </div>
  )
}
