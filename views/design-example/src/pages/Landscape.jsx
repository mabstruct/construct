import { useState, useMemo } from "react"
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area, Legend, Cell } from "recharts"

const LAYER_COLORS = {
  perception: "#f59e0b",
  spatial: "#06b6d4",
  worldModel: "#8b5cf6",
  language: "#ec4899",
  memory: "#10b981",
  agency: "#6366f1",
  action: "#ef4444",
  middleware: "#f97316",
}

const LAYER_LABELS = {
  perception: "Perception Layer",
  spatial: "Spatial Understanding",
  worldModel: "World Models",
  language: "Language Interface",
  memory: "Agent Memory",
  agency: "Agentic Systems",
  action: "Intent-to-Action",
  middleware: "Robot Middleware",
}

const stackLayers = [
  {
    id: "perception",
    name: "Perception & Detection",
    y: 1,
    maturity: 85,
    papers: 14,
    keyWork: ["YOLO family", "Segment Anything", "Grounding DINO", "RF-DETR", "Grounded SAM 2", "Dynamic-DINO", "YOLO-World"],
    insight: "The most mature layer. Two tracks coexist: the YOLO family anchors real-time closed-vocabulary detection (still the production default in robotics and industrial deployment), while Segment Anything, Grounding DINO, and their descendants have solved open-vocabulary detection and universal segmentation at the research level. The frontier has moved to grounding — connecting what's seen to what it means — and to bridges like YOLO-World that port real-time speed into the open-vocab regime.",
    status: "Mature",
  },
  {
    id: "spatial",
    name: "3D Spatial Understanding",
    y: 2,
    maturity: 70,
    papers: 16,
    keyWork: ["MASt3R-SLAM", "SpatialLM", "Locate 3D", "SceneVGGT", "Lp-SLAM", "VGGT"],
    insight: "Rapid convergence on transformer-based SLAM and language-perceptive 3D reconstruction. Depth estimation is well-covered. The interesting growth is semantic SLAM — fusing language, vision, and 3D into queryable scene representations.",
    status: "Converging",
  },
  {
    id: "worldModel",
    name: "World Models",
    y: 3,
    maturity: 45,
    papers: 28,
    keyWork: ["NVIDIA Cosmos", "DreamZero", "Causal WM", "LPWM", "V-JEPA 2", "PlayWorld", "Kairos 3.0"],
    insight: "The gravitational center of the field. Largest paper concentration. Four sub-paradigms competing: video prediction, latent dynamics, causal interventionist, and object-centric.",
    status: "Explosive Growth",
  },
  {
    id: "language",
    name: "Vision-Language Bridge",
    y: 4,
    maturity: 55,
    papers: 12,
    keyWork: ["3D-Grounded VL", "VLM-Loc", "OmniVLA", "ST4VLA", "SimVLA"],
    insight: "Language is becoming the universal interface between every layer. VLMs ground language in spatial representations. VLAs ground language in actions.",
    status: "Accelerating",
  },
  {
    id: "memory",
    name: "Agent Memory",
    y: 5,
    maturity: 30,
    papers: 10,
    keyWork: ["A-MEM", "AMA-Bench", "ReMEmbR", "STaR", "MEMENTO", "FindingDory"],
    insight: "The load-bearing wall that most systems don't have yet. Zettelkasten-style self-organizing memory, spatio-temporal retrieval, and the first benchmarks for evaluating it.",
    status: "Early but Critical",
  },
  {
    id: "agency",
    name: "Agentic Orchestration",
    y: 6,
    maturity: 40,
    papers: 11,
    keyWork: ["RACAS", "MALLVI", "ReAcTree", "MetaWorld-X", "MagicAgent", "BioProAgent"],
    insight: "Multi-agent coordination for robot control. Hierarchical planning trees. The shift from 'one model does everything' to 'specialized agents orchestrate through a shared protocol.'",
    status: "Structuring",
  },
  {
    id: "action",
    name: "Intent-to-Action",
    y: 7,
    maturity: 20,
    papers: 8,
    keyWork: ["DACo", "IntentCUA", "LLM-Planner", "Grounded Decoding", "MICoBot"],
    insight: "The critical gap. How does a natural language instruction become a sequence of motor commands? Hierarchical decomposition, skill abstraction, neuro-symbolic grounding.",
    status: "Critical Gap",
  },
  {
    id: "middleware",
    name: "Robot Middleware",
    y: 8,
    maturity: 15,
    papers: 5,
    keyWork: ["RACAS", "AgentRob", "OpenClaw", "PragmaBot"],
    insight: "The newest frontier. Agent frameworks as robot middleware — replacing ROS-style fixed pipelines with NL-driven, agentic control loops.",
    status: "Emerging",
  },
]

const convergenceData = [
  { name: "Feb 24", perception: 8, spatial: 5, worldModel: 3, language: 2, memory: 1, agency: 2, action: 0, middleware: 0 },
  { name: "Mar 1", perception: 12, spatial: 8, worldModel: 8, language: 4, memory: 4, agency: 4, action: 1, middleware: 0 },
  { name: "Mar 5", perception: 13, spatial: 11, worldModel: 14, language: 6, memory: 6, agency: 5, action: 2, middleware: 1 },
  { name: "Mar 9", perception: 14, spatial: 14, worldModel: 20, language: 9, memory: 8, agency: 7, action: 4, middleware: 3 },
  { name: "Mar 14", perception: 14, spatial: 16, worldModel: 28, language: 12, memory: 10, agency: 11, action: 8, middleware: 5 },
]

const paradigmShifts = [
  { year: "2019-22", paradigm: "Modular Pipelines", desc: "Perception, Planning, Control as separate, hand-engineered modules. ROS dominates." },
  { year: "2023", paradigm: "Foundation Model Arrival", desc: "SAM, GPT-4V, DINO prove pretrained models transfer to robotics. Everything gets a language interface." },
  { year: "2024", paradigm: "VLA Emergence", desc: "Vision-Language-Action models attempt end-to-end control. RT-2, Octo, OpenVLA. Results mixed but direction clear." },
  { year: "2025", paradigm: "World Model Convergence", desc: "World models become the substrate. Cosmos, SpatialLM. Causal reasoning enters." },
  { year: "2026", paradigm: "Agentic Integration", desc: "Multi-agent orchestration, intent decomposition, memory as infrastructure. The stack assembles." },
]

const researchFrontiers = [
  { name: "World Model\nArchitecture", x: 80, y: 85, z: 28, color: LAYER_COLORS.worldModel },
  { name: "Intent\nDecomposition", x: 30, y: 90, z: 8, color: LAYER_COLORS.action },
  { name: "Spatial\nGrounding", x: 70, y: 70, z: 16, color: LAYER_COLORS.spatial },
  { name: "Agent\nMemory", x: 40, y: 75, z: 10, color: LAYER_COLORS.memory },
  { name: "VLA\nPolicies", x: 65, y: 80, z: 12, color: LAYER_COLORS.language },
  { name: "Robot\nMiddleware", x: 20, y: 95, z: 5, color: LAYER_COLORS.middleware },
  { name: "Sim-to-Real", x: 50, y: 60, z: 6, color: "#64748b" },
  { name: "Causal\nReasoning", x: 55, y: 88, z: 10, color: LAYER_COLORS.worldModel },
]

const TAB = (active) => `px-4 py-2 text-sm font-medium rounded-t-lg cursor-pointer transition-all ${active ? "bg-purple-600/80 text-white" : "text-white/40 hover:text-white/70 hover:bg-white/[0.05]"}`

function StackView() {
  const [selected, setSelected] = useState(null)
  return (
    <div className="space-y-2">
      <p className="text-white/40 text-sm mb-4">Click any layer to see details. Layers ordered from raw perception (bottom) to high-level intent (top).</p>
      {[...stackLayers].reverse().map((layer) => (
        <div
          key={layer.id}
          onClick={() => setSelected(selected === layer.id ? null : layer.id)}
          className={`rounded-xl cursor-pointer transition-all border overflow-hidden ${selected === layer.id ? "border-purple-400/60" : "border-white/[0.08] hover:border-white/[0.15]"}`}
        >
          <div className="flex items-center gap-4 p-4" style={{ backgroundColor: `${LAYER_COLORS[layer.id]}10` }}>
            <div className="w-4 h-4 rounded-full shrink-0" style={{ backgroundColor: LAYER_COLORS[layer.id] }} />
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <span className="text-white font-semibold text-sm">{layer.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  layer.maturity > 70 ? "bg-green-900/50 text-green-300" :
                  layer.maturity > 40 ? "bg-yellow-900/50 text-yellow-300" :
                  layer.maturity > 25 ? "bg-orange-900/50 text-orange-300" :
                  "bg-red-900/50 text-red-300"
                }`}>{layer.status}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-white font-bold">{layer.papers}</div>
              <div className="text-white/30 text-xs">papers</div>
            </div>
            <div className="w-32">
              <div className="flex justify-between text-xs text-white/40 mb-1">
                <span>Maturity</span>
                <span>{layer.maturity}%</span>
              </div>
              <div className="w-full bg-white/[0.08] rounded-full h-2">
                <div className="h-2 rounded-full transition-all" style={{ width: `${layer.maturity}%`, backgroundColor: LAYER_COLORS[layer.id] }} />
              </div>
            </div>
          </div>
          {selected === layer.id && (
            <div className="p-4 bg-white/[0.03] border-t border-white/[0.06]">
              <p className="text-white/50 text-sm mb-3">{layer.insight}</p>
              <div className="flex flex-wrap gap-1">
                {layer.keyWork.map((p) => (
                  <span key={p} className="text-xs px-2 py-1 rounded bg-white/[0.06] text-white/50">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ConvergenceView() {
  return (
    <div className="space-y-6">
      <p className="text-white/40 text-sm">Cumulative paper count by layer over time. World models (purple) accelerate while perception (amber) plateaus — the field's gravity is shifting upward in the stack.</p>
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={convergenceData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" />
          <YAxis stroke="rgba(255,255,255,0.3)" />
          <Tooltip contentStyle={{ backgroundColor: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff" }} />
          <Legend wrapperStyle={{ color: "rgba(255,255,255,0.5)" }} />
          {Object.entries(LAYER_COLORS).map(([key, color]) => (
            <Area key={key} type="monotone" dataKey={key} stackId="1" stroke={color} fill={color} fillOpacity={0.3} name={LAYER_LABELS[key]} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function ParadigmView() {
  return (
    <div className="space-y-1">
      <p className="text-white/40 text-sm mb-4">The field's architectural paradigm shifts. Each era doesn't replace the last — it subsumes it.</p>
      {paradigmShifts.map((p, i) => {
        const colors = ["bg-gray-600", "bg-blue-600", "bg-cyan-600", "bg-purple-600", "bg-pink-600"]
        return (
          <div key={i} className="flex gap-4 items-stretch">
            <div className="w-20 shrink-0 text-right">
              <span className="text-white font-mono font-bold text-sm">{p.year}</span>
            </div>
            <div className="flex flex-col items-center">
              <div className={`w-4 h-4 rounded-full ${colors[i]} shrink-0 mt-1`} />
              {i < paradigmShifts.length - 1 && <div className="w-0.5 flex-1 bg-white/10" />}
            </div>
            <div className="flex-1 pb-6">
              <div className="text-white font-semibold">{p.paradigm}</div>
              <div className="text-white/40 text-sm mt-1">{p.desc}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function FrontierView() {
  return (
    <div className="space-y-4">
      <p className="text-white/40 text-sm">Research frontiers mapped by maturity (x) vs. activity (y). Bubble size = paper count. Upper-left quadrant: high urgency, low maturity.</p>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis type="number" dataKey="x" name="Maturity" domain={[0, 100]} stroke="rgba(255,255,255,0.3)" label={{ value: "Maturity", position: "bottom", fill: "rgba(255,255,255,0.3)", fontSize: 12 }} />
          <YAxis type="number" dataKey="y" name="Activity" domain={[50, 100]} stroke="rgba(255,255,255,0.3)" label={{ value: "Activity / Urgency", angle: -90, position: "left", fill: "rgba(255,255,255,0.3)", fontSize: 12 }} />
          <ZAxis type="number" dataKey="z" range={[100, 800]} />
          <Tooltip
            contentStyle={{ backgroundColor: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff" }}
            formatter={(value, name) => {
              if (name === "Maturity") return [`${value}%`, "Maturity"]
              if (name === "Activity") return [`${value}%`, "Activity"]
              return [value, name]
            }}
          />
          <Scatter data={researchFrontiers} shape="circle">
            {researchFrontiers.map((entry, i) => (
              <Cell key={i} fill={entry.color} fillOpacity={0.7} stroke={entry.color} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-4 gap-2">
        {researchFrontiers.map((f, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: f.color }} />
            <span className="text-white/50">{f.name.replace("\n", " ")}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ConnectionView() {
  const connections = [
    { from: "Perception", to: "Spatial Understanding", strength: "strong", label: "Depth + SLAM feed 3D reconstruction" },
    { from: "Spatial Understanding", to: "World Models", strength: "strong", label: "Scene representations become predictive models" },
    { from: "World Models", to: "VLA Policies", strength: "strong", label: "World models simulate, policies optimize" },
    { from: "Language", to: "Every Layer", strength: "strong", label: "NL as universal addressing protocol" },
    { from: "Memory", to: "Agency", strength: "moderate", label: "Memory enables long-horizon orchestration" },
    { from: "Agency", to: "Intent-to-Action", strength: "emerging", label: "Multi-agent decomposition of intent" },
    { from: "World Models", to: "Memory", strength: "emerging", label: "Predicted futures stored as experience" },
    { from: "Intent-to-Action", to: "Middleware", strength: "weak", label: "The missing integration layer" },
    { from: "Perception", to: "World Models", strength: "moderate", label: "Object-centric perception feeds causal models" },
    { from: "Sim-to-Real", to: "World Models", strength: "moderate", label: "Domain gap is the deployment bottleneck" },
  ]
  const strengthColors = { strong: "border-green-500/60 bg-green-950/30", moderate: "border-yellow-500/60 bg-yellow-950/30", emerging: "border-purple-500/60 bg-purple-950/30", weak: "border-red-500/60 bg-red-950/30" }
  const strengthLabels = { strong: "Established", moderate: "Growing", emerging: "Emerging", weak: "Critical Gap" }

  return (
    <div className="space-y-4">
      <p className="text-white/40 text-sm mb-2">Cross-layer connections identified from the corpus. Strength indicates how many papers bridge the two areas.</p>
      <div className="flex gap-3 mb-4">
        {Object.entries(strengthLabels).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 text-xs">
            <div className={`w-3 h-3 rounded border-2 ${strengthColors[k]}`} />
            <span className="text-white/40">{v}</span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {connections.map((c, i) => (
          <div key={i} className={`p-3 rounded-lg border-l-4 ${strengthColors[c.strength]}`}>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-white font-semibold">{c.from}</span>
              <span className="text-white/30">&rarr;</span>
              <span className="text-white font-semibold">{c.to}</span>
            </div>
            <div className="text-white/40 text-xs mt-1">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Landscape() {
  const [tab, setTab] = useState("stack")

  const tabs = [
    { id: "stack", label: "The Stack" },
    { id: "convergence", label: "Convergence" },
    { id: "paradigms", label: "Paradigm Shifts" },
    { id: "frontiers", label: "Research Frontiers" },
    { id: "connections", label: "Cross-Layer Links" },
  ]

  return (
    <div className="mx-auto max-w-5xl py-12">
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.04] text-xs text-white/40 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
          ISW Domain Analysis
        </div>
        <h1 className="font-display text-3xl md:text-4xl font-bold text-white mb-2">ISW Field Map — The Stack Assembles</h1>
        <p className="text-white/40 text-sm">Architectural overview of the Intelligent Semantic Worlds domain from 248+ papers across 8 layers.</p>
        <div className="h-px bg-gradient-to-r from-purple-600/50 via-pink-500/30 to-transparent mt-6" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Papers Reviewed", value: "248+", sub: "25 digest cycles", color: "#8B5CF6" },
          { label: "Stack Layers", value: "8", sub: "Perception to Intent", color: "#06B6D4" },
          { label: "Key Frontiers", value: "4", sub: "World models lead", color: "#F59E0B" },
          { label: "Critical Gaps", value: "3", sub: "Intent, Memory, Safety", color: "#EF4444" },
        ].map((s, i) => (
          <div key={i} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-white/60 text-sm font-medium">{s.label}</div>
            <div className="text-white/25 text-xs mt-1">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-1 mb-6 border-b border-white/[0.06] pb-px overflow-x-auto">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={TAB(tab === t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="glass rounded-2xl p-6 min-h-[400px]">
        {tab === "stack" && <StackView />}
        {tab === "convergence" && <ConvergenceView />}
        {tab === "paradigms" && <ParadigmView />}
        {tab === "frontiers" && <FrontierView />}
        {tab === "connections" && <ConnectionView />}
      </div>

      <div className="mt-6 text-center text-white/20 text-xs">
        MABSTRUCT — Watson v0.3.0 — ISW Field Synthesis — April 2026
      </div>
    </div>
  )
}
