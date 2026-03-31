"use client";

import Link from "next/link";

// Pre-populated demo data — no API calls needed
const DEMO_DATA = {
  total_sessions: 12,
  sessions_last_30_days: 8,
  avg_score_all_time: 68.4,
  best_session_score: 85,
  total_skills_tracked: 22,
  avg_skill_score: 62,
  weakest_skill: "tradeoff_analysis",
  strongest_skill: "star_structure",
  total_stories: 5,
  coverage_pct: 60,
  readiness_estimate: 58,
  total_cost_usd: 4.23,
  cost_last_30_days: 2.85,
  recent_sessions: [
    { type: "behavioral", score: 72, date: "Feb 24", status: "completed" },
    { type: "system_design", score: 65, date: "Feb 22", status: "completed" },
    { type: "behavioral", score: 78, date: "Feb 20", status: "completed" },
    { type: "negotiation", score: 55, date: "Feb 18", status: "completed" },
    { type: "system_design", score: 85, date: "Feb 15", status: "completed" },
  ],
  skills: [
    { name: "STAR Structure", category: "Structure", score: 82, trend: "improving" },
    { name: "Specificity", category: "Structure", score: 75, trend: "stable" },
    { name: "Result Presence", category: "Structure", score: 70, trend: "improving" },
    { name: "Tradeoff Analysis", category: "Depth", score: 45, trend: "declining" },
    { name: "Assumption Calling", category: "Depth", score: 52, trend: "stable" },
    { name: "Follow-up Readiness", category: "Depth", score: 60, trend: "improving" },
    { name: "Clarity", category: "Communication", score: 78, trend: "stable" },
    { name: "Ownership Language", category: "Communication", score: 65, trend: "improving" },
    { name: "Scale Thinking", category: "Seniority", score: 48, trend: "declining" },
    { name: "Mentoring Signals", category: "Seniority", score: 55, trend: "stable" },
  ],
};

const TYPE_LABELS: Record<string, string> = {
  behavioral: "Behavioral",
  system_design: "System Design",
  negotiation: "Negotiation",
};

const TREND_ICON: Record<string, { icon: string; color: string }> = {
  improving: { icon: "\u2191", color: "text-green-600" },
  declining: { icon: "\u2193", color: "text-red-500" },
  stable: { icon: "\u2192", color: "text-slate-400" },
};

export default function DemoPage() {
  const d = DEMO_DATA;
  const readinessColor = d.readiness_estimate >= 70 ? "from-green-400 to-green-500"
    : d.readiness_estimate >= 50 ? "from-yellow-400 to-amber-500"
    : "from-red-400 to-red-500";

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Nav */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 px-4 py-2.5 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href="/" className="text-lg font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
            InterviewCraft
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 bg-amber-50 text-amber-600 px-2 py-1 rounded-full font-medium">Demo Mode</span>
            <Link href="/login" className="px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-lg text-sm font-medium hover:from-indigo-700 hover:to-violet-700 shadow-sm shadow-indigo-200">
              Sign up free
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Readiness */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Readiness Estimate</p>
              <p className="text-sm text-slate-400 mt-0.5">Based on 12 sessions, 22 skills, 5 stories</p>
            </div>
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
              d.readiness_estimate >= 70 ? "bg-green-100 text-green-700" :
              d.readiness_estimate >= 50 ? "bg-yellow-100 text-yellow-700" :
              "bg-red-50 text-red-600"
            }`}>
              {d.readiness_estimate >= 70 ? "Interview Ready" : d.readiness_estimate >= 50 ? "Getting There" : "Keep Practicing"}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
              <div className={`h-full rounded-full bg-gradient-to-r ${readinessColor} transition-all duration-1000`}
                   style={{ width: `${d.readiness_estimate}%` }} />
            </div>
            <span className="text-2xl font-bold text-slate-800">{d.readiness_estimate}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Sessions", value: d.total_sessions, sub: `${d.sessions_last_30_days} last 30d` },
            { label: "Avg Score", value: d.avg_score_all_time.toFixed(1), sub: `Best: ${d.best_session_score}` },
            { label: "Skills", value: d.total_skills_tracked, sub: `Avg: ${d.avg_skill_score}` },
            { label: "Stories", value: d.total_stories, sub: `${d.coverage_pct}% coverage` },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-4">
              <p className="text-xs text-slate-400 mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-slate-800">{s.value}</p>
              <p className="text-xs text-slate-400 mt-0.5">{s.sub}</p>
            </div>
          ))}
        </div>

        {/* Skills snapshot */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Skill Graph (22 microskills)</h2>
          <div className="space-y-2">
            {d.skills.map((s) => {
              const t = TREND_ICON[s.trend];
              return (
                <div key={s.name} className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 w-24 shrink-0">{s.category}</span>
                  <span className="text-sm text-slate-700 w-40 shrink-0">{s.name}</span>
                  <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        s.score >= 70 ? "bg-green-400" : s.score >= 50 ? "bg-yellow-400" : "bg-red-400"
                      }`}
                      style={{ width: `${s.score}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-slate-600 w-8 text-right">{s.score}</span>
                  <span className={`text-xs font-bold w-4 ${t.color}`}>{t.icon}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent sessions */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Recent Sessions</h2>
          <div className="space-y-2">
            {d.recent_sessions.map((s, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-slate-50 transition-colors">
                <div>
                  <p className="text-sm font-medium text-slate-700">{TYPE_LABELS[s.type] ?? s.type}</p>
                  <p className="text-xs text-slate-400">{s.date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-bold font-mono ${
                    s.score >= 80 ? "text-green-600" : s.score >= 60 ? "text-yellow-600" : "text-red-500"
                  }`}>{s.score}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{s.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cost */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">API Cost Tracking</h2>
          <div className="flex gap-8 text-sm">
            <div>
              <p className="text-xs text-slate-400">Total Spent</p>
              <p className="font-mono font-bold text-slate-800">${d.total_cost_usd.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Last 30 days</p>
              <p className="font-mono font-bold text-slate-800">${d.cost_last_30_days.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Per session avg</p>
              <p className="font-mono font-bold text-slate-800">${(d.total_cost_usd / d.total_sessions).toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-r from-indigo-600 to-violet-600 rounded-2xl p-8 text-center shadow-lg shadow-indigo-200/50">
          <h2 className="text-xl font-bold text-white mb-2">This could be your data</h2>
          <p className="text-indigo-100 text-sm mb-6">Start your first 5-minute diagnostic session and build your personal skill graph.</p>
          <Link href="/login" className="inline-block px-6 py-3 bg-white text-indigo-700 rounded-xl font-medium hover:bg-indigo-50 transition-colors shadow-sm">
            Start practicing free
          </Link>
        </div>
      </div>
    </main>
  );
}
