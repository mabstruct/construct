import { useState, useMemo } from 'react'
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts'

// ── Embedded data ──────────────────────────────────────────────────────────
const CLUSTER_DATA = {
  'embodied-ai': {
    name: 'Embodied AI & Home Robotics', count: 28, color: '#8B5CF6',
    topPapers: [
      'NVIDIA Cosmos: World Foundation Models for Physical AI',
      'Gemini Robotics: Bringing AI into the Physical World',
      'Habitat 3.0: A Co-Habitat for Humans, Avatars and Robots',
      'SpatialLM: Training Large Language Models for Structured Indoor Modeling',
      'Robotic World Model: A Neural Network Simulator',
      'WorldEval: World Model as Robot Policies Evaluator',
      'Hierarchical Vision-Language Planning for Multi-Step Humanoid Manipulation'
    ]
  },
  'spatial-understanding': {
    name: '3D Spatial Understanding & Scene Modeling', count: 14, color: '#F43F5E',
    topPapers: [
      'MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction',
      'Locate 3D: Real-World Object Localization via Self-Supervised Learning',
      'SceneVGGT: VGGT-based online 3D semantic SLAM',
      'GSMem: 3D Gaussian Splatting as Persistent Spatial Memory',
      'Asset-Centric Metric-Semantic Maps of Indoor Environments',
      'DepthART: Monocular Depth Estimation as Autoregressive Refinement'
    ]
  },
  'perception-detection': {
    name: 'Visual Perception & Object Detection', count: 8, color: '#F97316',
    topPapers: [
      'Grounding DINO: Marrying DINO with Grounded Language Models',
      'RF-DETR: Neural Architecture Search for Real-Time Detection Transformers',
      'Segment Anything (SAM)',
      'Grounded SAM 2: From Open-Set Detection to Segmentation and Tracking',
      'Dynamic-DINO: Fine-Grained Mixture of Experts Tuning'
    ]
  },
  'agentic-systems': {
    name: 'Agentic AI Systems', count: 10, color: '#10B981',
    topPapers: [
      'AI Agent Systems: Architectures, Applications, and Evaluation',
      'AMA-Bench: Evaluating Long-Horizon Memory for Agentic Applications',
      'A-MEM: Agentic Memory for LLM Agents',
      'RACAS: Robot-Agnostic Control with Agentic Architecture',
      'From Prompts to Production: Agentic Development Playbook'
    ]
  },
  'vision-language': {
    name: 'Vision-Language Models', count: 6, color: '#06B6D4',
    topPapers: [
      '3D-Grounded Vision-Language Framework for Robotic Task Planning',
      'MAPG: Multi-Agent Probabilistic Grounding for VLN',
      'OmniVLA: Unified Language, Spatial Coordinates, and Visual Goals',
      'Physically Grounded Vision-Language Models for Robotic Manipulation'
    ]
  },
  'robot-learning': {
    name: 'Robot Learning & Training', count: 5, color: '#3B82F6',
    topPapers: [
      'RoboGen: Towards Unleashing Infinite Data for Automated Robot Learning',
      'DreamZero: World Action Model with Zero-Shot Robot Policies',
      'PlayWorld: World Models from Autonomous Robot Self-Play',
      'How to Train Your Robot with Deep Reinforcement Learning'
    ]
  },
  'intent-to-action': {
    name: 'Intent-to-Action & Task Decomposition', count: 8, color: '#FBBF24',
    topPapers: [
      'DACo: Dual-Agent Framework for Deliberation and Grounding',
      'LLM-Planner: Hierarchical Planning with Cross-Attention Grounding',
      'Grounded Decoding: Constraining LLM for Feasible Robot Actions',
      'BioProAgent: Finite State Machine-Anchored Agentic Planning'
    ]
  },
  'indoor-world-model': {
    name: 'Indoor World Models', count: 6, color: '#EC4899',
    topPapers: [
      'SpatialLM: LLMs for Structured Indoor Modeling',
      'MotionAnymesh: Physics-Grounded Articulation for Digital Twins',
      'GSMem: 3D Gaussian Splatting as Persistent Spatial Memory',
      'Newton 1.0: GPU-accelerated Physics Engine'
    ]
  },
  'causal-world-models': {
    name: 'Causal World Models', count: 4, color: '#14B8A6',
    topPapers: [
      'Causal World Modeling for Robot Control',
      'Causal-JEPA: Object-Level Masking as Causal Intervention',
      'ADAM: LLM-based Causal Discovery in Open-World Environments'
    ]
  },
  'agentic-robot-middleware': {
    name: 'Agentic Robot Middleware', count: 5, color: '#F472B6',
    topPapers: [
      'AgentRob: LLM Agents to Physical Robots via MCP',
      'OpenClaw: Agent-Native Robot Middleware',
      'CORE: Contextual Safety Reasoning for Open-World Robots',
      'PragmaBot: Verbal Reinforcement Learning'
    ]
  },
  'autonomous-sim-loops': {
    name: 'Autonomous Simulation Loops', count: 3, color: '#84CC16',
    topPapers: [
      'World4RL: Diffusion World Models for Policy Refinement',
      'DreamDojo Platform for Scalable Robot Training',
      'Closed-Loop Sim Platforms for Robot Policy Training (Isaac Sim, MuJoCo, Unity)'
    ]
  },
  'foundations-training': {
    name: 'ML Foundations & Data', count: 4, color: '#A78BFA',
    topPapers: [
      'Rethinking Atrous Convolution for Semantic Image Segmentation',
      'A fast learning algorithm for deep belief nets',
      'Exploring the efficacy of base data augmentation methods'
    ]
  },
  'robot-navigation': {
    name: 'Robot Navigation & Motion Planning', count: 1, color: '#EF4444',
    topPapers: ['Robotic Motion Planning: C-Space Fundamentals']
  },
  'spatial-rag-robotics': {
    name: 'Spatial RAG for Robot Task Planning', count: 3, color: '#D946EF',
    topPapers: [
      'Embodied-RAG: Non-parametric Memory for Navigation and Explanation',
      'RoboEXP: Action-Conditioned Scene Graph for Robotic Manipulation',
      'Open-Vocabulary Functional 3D Scene Graphs for Real-World Indoor Spaces'
    ]
  }
}

const TIMELINE_DATA = [
  { year: 2006, 'foundations-training': 1, total: 1 },
  { year: 2019, 'embodied-ai': 1, total: 1 },
  { year: 2021, 'robot-learning': 1, total: 1 },
  { year: 2022, 'embodied-ai': 1, total: 1 },
  { year: 2023, 'embodied-ai': 2, 'vision-language': 1, 'foundations-training': 1, total: 4 },
  { year: 2024, 'embodied-ai': 4, 'perception-detection': 2, 'agentic-systems': 2, 'spatial-understanding': 3, 'robot-learning': 2, 'vision-language': 1, total: 14 },
  { year: 2025, 'embodied-ai': 14, 'perception-detection': 3, 'agentic-systems': 4, 'spatial-understanding': 5, 'foundations-training': 1, 'vision-language': 2, 'robot-learning': 2, 'intent-to-action': 3, 'causal-world-models': 2, total: 36 },
  { year: 2026, 'embodied-ai': 6, 'perception-detection': 1, 'agentic-systems': 4, 'spatial-understanding': 4, 'intent-to-action': 5, 'indoor-world-model': 4, 'causal-world-models': 2, 'agentic-robot-middleware': 5, 'vision-language': 3, 'spatial-rag-robotics': 3, total: 37 }
]

const CROSS_THEMES = [
  { name: 'World Model Convergence', description: 'World models converging across robot learning, embodied AI, spatial understanding, and causal reasoning — the gravitational center of the field', papers: 22, strength: 'dominant' },
  { name: 'Language as Universal Interface', description: 'Language as the protocol between every layer: Lp-SLAM, SpatialLM, MAPG, VLAs, agent-to-agent communication', papers: 18, strength: 'strong' },
  { name: 'Agent Memory as Infrastructure', description: 'Memory is not a feature but infrastructure. ReMEmbR, A-MEM, AMA-Bench, GSMem, MemOS — the missing layer for long-horizon tasks', papers: 12, strength: 'strong' },
  { name: 'Foundation Models as Substrate', description: '~50% of 190+ papers build on foundation models. No longer a theme — the default assumption for all new work', papers: 95, strength: 'dominant' },
  { name: 'Agentic Middleware Emergence', description: 'The orchestration layer between planning and control is becoming a field: AgentRob, OpenClaw, CORE, PragmaBot', papers: 10, strength: 'emerging' },
  { name: 'Intent-to-Action Pipeline', description: 'From natural language to executable robot steps. DACo, LLM-Planner, Grounded Decoding — the primary research focus', papers: 14, strength: 'strong' }
]

const RESEARCH_GAPS = [
  { title: 'Multi-Robot Coordination', status: 'critical', description: 'No coverage of swarm, fleet, or multi-agent coordination systems. Real deployment involves multiple robots in shared spaces.', opportunity: 'High priority gap in collaborative robotics and distributed embodied AI.' },
  { title: 'Safety & Ethics of Embodied AI', status: 'critical', description: 'Not a single paper addresses dangerous robot decisions. No safety constraints for intent-to-action. No ethical framework for autonomous household systems.', opportunity: 'A field building systems that act in physical space with humans cannot avoid this indefinitely.' },
  { title: 'Outdoor Environments', status: 'critical', description: 'Entire corpus is indoor-focused. Architectural assumptions (structured geometry, stable lighting, known objects) will not transfer.', opportunity: 'Extension to logistics, agriculture, construction, and urban environments.' },
  { title: 'True Memory Consolidation', status: 'critical', description: 'No AI system implements multi-speed complementary learning, replay-driven consolidation, or principled forgetting. Current memory is storage, not memory.', opportunity: 'The hippocampus-for-LLM research program — building fast episodic + slow semantic systems with replay.' },
  { title: 'Human Intent Disambiguation', status: 'important', description: '"Put that over there" requires resolving three references under uncertainty. Only MICoBot addresses mixed-initiative dialog for clarification.', opportunity: 'Essential for real household deployment. Conversational grounding of underspecified commands.' },
  { title: 'Sim-to-Real Transfer', status: 'important', description: 'The domain gap between simulation and reality is mentioned everywhere but has no dedicated coverage. Critical bottleneck as world models go from lab to deployment.', opportunity: 'Emerging as key challenge with world model convergence accelerating.' },
  { title: 'Failure Recovery & Replanning', status: 'important', description: 'What does the robot do when an action fails? Replanning, error detection, graceful degradation — almost no dedicated research.', opportunity: 'Essential for robustness in unstructured real-world environments.' },
  { title: 'Affordance Reasoning', status: 'important', description: 'How robots understand what actions are physically possible given state and objects. Added as wildcard in v2 pattern.', opportunity: 'Key bridge between world models and intent-to-action planning.' }
]

const TAG_CLOUD_DATA = [
  { tag: 'foundation-models', weight: 0.15, topic: 'embodied-ai' },
  { tag: 'world-models', weight: 0.14, topic: 'world-models' },
  { tag: 'intent-to-action', weight: 0.13, topic: 'intent' },
  { tag: 'object-detection', weight: 0.12, topic: 'perception' },
  { tag: 'multimodal', weight: 0.10, topic: 'embodied-ai' },
  { tag: 'transformers', weight: 0.12, topic: 'perception' },
  { tag: 'grounding', weight: 0.11, topic: 'vision-language' },
  { tag: 'depth-estimation', weight: 0.08, topic: 'spatial' },
  { tag: 'slam', weight: 0.10, topic: 'spatial' },
  { tag: 'simulation', weight: 0.12, topic: 'embodied-ai' },
  { tag: 'causal-reasoning', weight: 0.10, topic: 'world-models' },
  { tag: 'agent-architecture', weight: 0.10, topic: 'agentic' },
  { tag: 'segmentation', weight: 0.10, topic: 'perception' },
  { tag: 'robot-middleware', weight: 0.09, topic: 'middleware' },
  { tag: 'memory-systems', weight: 0.11, topic: 'agentic' },
  { tag: 'scene-modeling', weight: 0.08, topic: 'spatial' },
  { tag: 'digital-twins', weight: 0.09, topic: 'world-models' },
  { tag: 'task-decomposition', weight: 0.10, topic: 'intent' },
  { tag: 'reinforcement-learning', weight: 0.10, topic: 'robot-learning' },
  { tag: 'human-robot-collaboration', weight: 0.08, topic: 'embodied-ai' },
  { tag: 'real-time', weight: 0.08, topic: 'perception' },
  { tag: 'gaussian-splatting', weight: 0.08, topic: 'spatial' },
  { tag: 'knowledge-base', weight: 0.07, topic: 'agentic' },
  { tag: 'sim-loops', weight: 0.08, topic: 'simulation' },
  { tag: 'game-engine-sim', weight: 0.06, topic: 'simulation' },
  { tag: 'spatial-rag', weight: 0.09, topic: 'spatial-rag' },
  { tag: 'scene-graphs', weight: 0.08, topic: 'spatial-rag' }
]

const TOPIC_COLORS = {
  'embodied-ai': '#8B5CF6', perception: '#F97316', spatial: '#F43F5E',
  'vision-language': '#06B6D4', agentic: '#10B981', 'robot-learning': '#3B82F6',
  'robot-navigation': '#EF4444', foundations: '#A78BFA',
  'world-models': '#EC4899', intent: '#FBBF24', middleware: '#F472B6',
  simulation: '#84CC16',
  'spatial-rag': '#D946EF'
}

// ── Sub-views ──────────────────────────────────────────────────────────────
const tooltipStyle = {
  backgroundColor: 'rgba(5,5,7,0.9)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', backdropFilter: 'blur(20px)'
}

function Overview({ clusterChartData }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total Entries', value: '210+', sub: '30 daily digests · 14 clusters', color: 'violet' },
          { label: 'Research Clusters', value: '14', sub: 'Search pattern v8 · weighted', color: 'cyan' },
          { label: 'Knowledge Cards', value: '19', sub: '22 connections · 6 types', color: 'orange' }
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-5">
            <p className="text-white/40 text-sm">{s.label}</p>
            <p className={`text-3xl font-bold mt-1 text-${s.color}`}>{s.value}</p>
            <p className="text-xs text-white/40 mt-2">{s.sub}</p>
          </div>
        ))}
      </div>

      <div className="glass rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Cluster Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={clusterChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
            <XAxis dataKey="name" stroke="#94A3B8" angle={-35} textAnchor="end" height={100} tick={{ fontSize: 11 }} />
            <YAxis stroke="#94A3B8" />
            <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: '#E2E8F0' }} formatter={v => [`${v} papers`, 'Count']} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {clusterChartData.map((e, i) => <Cell key={i} fill={e.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function ClusterMap() {
  return (
    <div className="space-y-4">
      {Object.entries(CLUSTER_DATA).map(([key, cluster]) => (
        <div key={key} className="glass rounded-xl p-5 hover:border-muted/40 transition">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-lg font-semibold text-white">{cluster.name}</h3>
              <p className="text-sm text-white/40 mt-1">{cluster.count} papers · {Math.round((cluster.count / Object.values(CLUSTER_DATA).reduce((s, c) => s + c.count, 0)) * 100)}% of structured corpus</p>
            </div>
            <span className="text-sm font-medium px-3 py-1 rounded-full" style={{ backgroundColor: cluster.color + '20', color: cluster.color, border: `1px solid ${cluster.color}40` }}>
              {cluster.count}
            </span>
          </div>
          <div className="space-y-1.5 mt-3">
            <p className="text-xs text-white/40 font-semibold uppercase tracking-wider">Key Papers</p>
            {cluster.topPapers.slice(0, 5).map((paper, i) => (
              <p key={i} className="text-sm text-text/80 flex items-start gap-2">
                <span className="text-violet mt-0.5">·</span>{paper}
              </p>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function Timeline({ yearChartData }) {
  return (
    <div className="glass rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Publication Year Distribution</h3>
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={yearChartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
          <XAxis dataKey="year" stroke="#94A3B8" />
          <YAxis stroke="#94A3B8" />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: '#E2E8F0' }} />
          <Legend />
          <Area type="monotone" dataKey="Embodied AI" stackId="1" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.6} />
          <Area type="monotone" dataKey="Spatial" stackId="1" stroke="#F43F5E" fill="#F43F5E" fillOpacity={0.6} />
          <Area type="monotone" dataKey="Perception" stackId="1" stroke="#F97316" fill="#F97316" fillOpacity={0.6} />
          <Area type="monotone" dataKey="Agentic" stackId="1" stroke="#10B981" fill="#10B981" fillOpacity={0.6} />
          <Area type="monotone" dataKey="Robot Learning" stackId="1" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.6} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function CrossThemes() {
  const strengthStyles = {
    dominant: { bg: 'bg-violet/10', border: 'border-violet/30', badge: 'text-violet bg-violet/20' },
    strong: { bg: 'bg-cyan/10', border: 'border-cyan/30', badge: 'text-cyan bg-cyan/20' },
    emerging: { bg: 'bg-white/[0.02]', border: 'border-white/[0.08]', badge: 'text-white/40 bg-white/[0.04]' }
  }

  return (
    <div className="space-y-4">
      {CROSS_THEMES.map((theme, i) => {
        const s = strengthStyles[theme.strength]
        return (
          <div key={i} className={`rounded-xl p-5 border ${s.bg} ${s.border}`}>
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-lg font-semibold text-white">{theme.name}</h3>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${s.badge}`}>{theme.strength}</span>
                <span className="text-xs text-white/40">{theme.papers} papers</span>
              </div>
            </div>
            <p className="text-sm text-text/80">{theme.description}</p>
          </div>
        )
      })}
    </div>
  )
}

function TagCloud() {
  const sorted = [...TAG_CLOUD_DATA].sort((a, b) => b.weight - a.weight)
  return (
    <div className="glass rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-6">Tags by Weight & Topic</h3>
      <div className="flex flex-wrap gap-3 justify-center">
        {sorted.map((item, i) => {
          const size = 0.8 + item.weight * 1.5
          const color = TOPIC_COLORS[item.topic] || '#94A3B8'
          return (
            <span key={i} className="px-4 py-2 rounded-full border transition hover:scale-105 cursor-default"
              style={{ fontSize: `${size}rem`, borderColor: color, color, backgroundColor: color + '15' }}>
              {item.tag.replace(/-/g, ' ')}
            </span>
          )
        })}
      </div>
      <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        {Object.entries(TOPIC_COLORS).map(([key, color]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-white/40 capitalize">{key.replace(/-/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResearchGaps() {
  return (
    <div className="space-y-4">
      {RESEARCH_GAPS.map((gap, i) => {
        const critical = gap.status === 'critical'
        return (
          <div key={i} className={`rounded-xl p-5 border ${critical ? 'bg-rose/5 border-rose/30' : 'bg-orange/5 border-orange/30'}`}>
            <div className="flex items-start gap-3 mb-3">
              <span className={`text-lg mt-0.5 ${critical ? 'text-rose' : 'text-orange'}`}>{critical ? '●' : '◐'}</span>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white">{gap.title}</h3>
                <p className={`text-xs font-semibold mt-1 ${critical ? 'text-rose' : 'text-orange'}`}>
                  {critical ? 'Critical Gap' : 'Important Gap'}
                </p>
              </div>
            </div>
            <p className="text-sm text-text/80 mb-3">{gap.description}</p>
            <div className="bg-dark/60 rounded-lg p-3 border-l-2 border-violet">
              <p className="text-sm text-violet/90"><span className="font-semibold text-violet">Opportunity:</span> {gap.opportunity}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────
const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'clusters', label: 'Clusters' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'themes', label: 'Cross-Themes' },
  { id: 'tags', label: 'Tag Cloud' },
  { id: 'gaps', label: 'Research Gaps' }
]

export default function ISWLandscape() {
  const [view, setView] = useState('overview')

  const clusterChartData = useMemo(() =>
    Object.entries(CLUSTER_DATA).map(([, d]) => ({
      name: d.name.split('&')[0].trim(),
      value: d.count, color: d.color
    })), [])

  const yearChartData = useMemo(() =>
    TIMELINE_DATA.map(d => ({
      year: d.year,
      'Embodied AI': d['embodied-ai'] || 0,
      'Spatial': d['spatial-understanding'] || 0,
      'Perception': d['perception-detection'] || 0,
      'Agentic': d['agentic-systems'] || 0,
      'Robot Learning': d['robot-learning'] || 0
    })), [])

  return (
    <div>
      {/* Sub-nav */}
      <div className="flex flex-wrap gap-1.5 mb-6 bg-white/[0.02] rounded-lg p-1 border border-white/[0.08]">
        {sections.map(s => (
          <button key={s.id} onClick={() => setView(s.id)}
            className={`text-xs px-3 py-1.5 rounded-md transition font-medium ${
              view === s.id ? 'bg-violet/20 text-violet border border-violet/30' : 'text-white/40 hover:text-white/80'
            }`}>
            {s.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {view === 'overview' && <Overview clusterChartData={clusterChartData} />}
      {view === 'clusters' && <ClusterMap />}
      {view === 'timeline' && <Timeline yearChartData={yearChartData} />}
      {view === 'themes' && <CrossThemes />}
      {view === 'tags' && <TagCloud />}
      {view === 'gaps' && <ResearchGaps />}
    </div>
  )
}
