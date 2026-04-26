import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import digests from '../data/digests.json'
import articles from '../data/articles.json'

const stats = [
  { label: 'Blog Posts', value: articles.length.toString(), color: '#06B6D4' },
  { label: 'Daily Digests', value: digests.length.toString(), color: '#8B5CF6' },
  { label: 'Papers Tracked', value: digests.reduce((s, d) => s + d.candidates.length, 0).toString(), color: '#F97316' },
  { label: 'Search Pattern', value: 'v9', color: '#10B981' },
]

const sections = [
  { to: '/digests', title: 'ISW Research Digests', desc: 'Daily automated research digests from the ISW domain. Each digest surfaces the most relevant new papers and articles.', accent: 'from-emerald-400/20 via-teal-400/20 to-cyan-400/20' },
  { to: '/analysis', title: 'ISW Research Analysis', desc: 'Landscape analysis of the ISW corpus — clusters, taxonomy, gaps, timeline, and cross-cutting themes.', accent: 'from-amber-400/20 via-rose-400/20 to-fuchsia-500/20' },
  { to: '/landscape', title: 'ISW Landscape', desc: 'The eight-layer stack of embodied AI — from perception to robot middleware. Maturity scores, convergence trends, and research frontiers.', accent: 'from-purple-500/30 via-pink-400/20 to-amber-500/20' },
  { to: '/knowledge-graph', title: 'Knowledge Graph', desc: '25 knowledge cards, 45 typed connections. Interactive force-directed graph of themes, findings, gaps, provocations, and methods.', accent: 'from-cyan-500/30 via-indigo-400/20 to-purple-500/20' },
  { to: '/thought-stream', title: 'Thought Stream', desc: 'Ideas, essays, and reflections across mathematics, cosmology, philosophy, arts, and AI — indexed by date, register, and domain.', accent: 'from-fuchsia-500/30 via-cyan-400/20 to-indigo-500/30' },
  { to: '/architecture', title: 'CONSTRUCT Architecture', desc: 'How the autonomous research engine works — multi-agent system, daily pipeline, adaptation, infrastructure.', accent: 'from-cyan-400/20 via-sky-400/20 to-indigo-500/20' },
]

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl">
      {/* Hero */}
      <section className="py-16 md:py-24">
        <div className="max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.04] text-xs text-white/40">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Autonomous research engine active
          </div>

          <h1 className="font-display text-4xl md:text-6xl font-bold text-white leading-[1.05]">
            MABSTRUCT / CONSTRUCT
          </h1>
          <p className="text-sm md:text-base tracking-[0.12em] text-white/35 uppercase">AI-based Knowledge Management System</p>

          <p className="text-base md:text-lg text-white/50 max-w-2xl leading-relaxed">
            Findings, research results and blog posts are published automatically. MABSTRUCT can make mistakes.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <Link to="/thought-stream" className="inline-flex items-center gap-2 rounded-full bg-white text-black px-5 py-2.5 text-sm font-medium hover:bg-white/90 transition">
              Enter the thought stream <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/analysis" className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] text-white/80 px-5 py-2.5 text-sm hover:bg-white/[0.08] transition">
              Research analysis <Sparkles className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="pb-12">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stats.map(s => (
            <div key={s.label} className="glass rounded-xl p-5">
              <div className="text-3xl font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="text-xs text-white/35 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* About */}
      <section className="pb-12">
        <div className="glass rounded-2xl p-6 md:p-8">
          <div className="flex items-center gap-2 mb-5">
            <Sparkles className="h-4 w-4 text-white/40" />
            <span className="text-xs tracking-[0.2em] text-white/35 uppercase">About the Project</span>
          </div>
          <div className="space-y-4 text-sm text-white/50 leading-relaxed max-w-3xl">
            <p>
              <strong className="text-white">CONSTRUCT</strong> is an AI-based knowledge management system designed for human–AI research collaboration. CONSTRUCT uses a multi-agent architecture where specialized AI agents handle different cognitive functions — one finds, one thinks, one curates, one writes — while the human retains editorial authority and strategic direction. The system maintains a living knowledge graph: vetted cards with typed connections, confidence levels, gap identification, and cross-domain pattern detection. It doesn't replace the researcher's judgment. It extends their reach.
            </p>
            <p>
              <em className="text-white/60">Intelligent Semantic Worlds</em> (ISW) as an active research domain is actually a blade sharpener for hardening the capabilities of MABSTRUCT/CONSTRUCT as an autonomous agentic research system.
            </p>
          </div>
        </div>
      </section>

      {/* Explore cards */}
      <section className="pb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-display text-2xl text-white">Explore</h2>
        </div>
        <div className="grid sm:grid-cols-2 gap-5">
          {sections.map(s => (
            <Link
              key={s.to}
              to={s.to}
              className="glass glass-hover group relative overflow-hidden p-6 transition-all duration-300 hover:-translate-y-1"
            >
              <div className={`absolute inset-0 bg-gradient-to-br opacity-60 ${s.accent}`} />
              <div className="relative">
                <h3 className="font-display text-xl text-white font-semibold mb-2">{s.title}</h3>
                <p className="text-sm text-white/40 leading-relaxed">{s.desc}</p>
                <div className="flex items-center gap-1 mt-4 text-xs text-white/30 group-hover:text-white/60 transition">
                  Explore <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Recent Activity */}
      <section className="pb-20">
        <h2 className="font-display text-2xl text-white mb-6">Recent Activity</h2>
        <div className="space-y-3">
          {digests.slice(0, 5).map(d => (
            <Link
              key={d.date}
              to={`/digests/${d.date}`}
              className="glass glass-hover flex items-start gap-4 rounded-xl p-4 transition-all group"
            >
              <div className="text-xs text-white/30 font-mono whitespace-nowrap pt-0.5">{d.date}</div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white/80 group-hover:text-white transition truncate">
                  {d.theme || 'Daily research digest'}
                </div>
                <div className="text-xs text-white/30 mt-1">
                  {d.candidates.length} candidates — {d.candidates.filter(c => c.relevance >= 5).length} top-rated
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
