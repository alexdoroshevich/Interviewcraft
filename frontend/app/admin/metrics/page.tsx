"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";

// ── Types ─────────────────────────────────────────────────────────────────────

interface LatencyPercentiles { p50: number | null; p95: number | null }
interface VoiceLatencyMetrics {
  stt: LatencyPercentiles; llm_ttft: LatencyPercentiles;
  tts: LatencyPercentiles; e2e: LatencyPercentiles; sample_count: number;
}
interface ScoringMetrics {
  avg_score: number | null; score_stddev: number | null;
  total_scored: number; rewind_rate_pct: number;
}
interface UsageMetrics {
  total_sessions: number; completed_sessions: number;
  completion_rate_pct: number; total_cost_usd: number;
  cost_per_session_usd: number; cache_hit_rate_pct: number; total_api_calls: number;
}
interface DailyLatencyPoint { date: string; e2e_p50: number | null; e2e_p95: number | null }
interface AdminMetrics {
  voice_7d: VoiceLatencyMetrics; scoring_30d: ScoringMetrics;
  usage_30d: UsageMetrics; latency_trend: DailyLatencyPoint[];
  kpi_latency_ok: boolean; kpi_cache_ok: boolean; kpi_completion_ok: boolean;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
      ok ? "bg-green-100 text-green-800" : "bg-red-50 text-red-700"
    }`}>
      <span>{ok ? "✓" : "✗"}</span> {label}
    </span>
  );
}

function MetricCard({ label, value, sub, warn }: {
  label: string; value: string; sub?: string; warn?: boolean
}) {
  return (
    <div className={`card p-4 ${warn ? "border-red-200" : ""}`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold font-mono ${warn ? "text-red-600" : "text-slate-800"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function LatencyRow({ label, data }: { label: string; data: LatencyPercentiles }) {
  const p95Warn = data.p95 !== null && data.p95 >= 1000;
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-600 w-24">{label}</span>
      <div className="flex gap-6">
        <div className="text-center">
          <p className="text-xs text-slate-400">p50</p>
          <p className="text-sm font-mono font-medium text-slate-700">
            {data.p50 !== null ? `${data.p50}ms` : "—"}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-slate-400">p95</p>
          <p className={`text-sm font-mono font-medium ${p95Warn ? "text-red-600" : "text-slate-700"}`}>
            {data.p95 !== null ? `${data.p95}ms` : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminMetricsPage() {
  const { ready } = useAuth();
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  function fetchMetrics() {
    setLoading(true);
    api.admin.metrics()
      .then((m) => { setMetrics(m); setLastUpdated(new Date()); })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!ready) return;
    fetchMetrics();
  }, [ready]);

  if (loading) return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-5xl mx-auto space-y-3 animate-pulse">
        {[...Array(4)].map((_, i) => <div key={i} className="h-32 bg-slate-200 rounded-xl" />)}
      </div>
    </main>
  );

  if (error || !metrics) return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
      <p className="text-red-600">{error ?? "Failed to load metrics"}</p>
    </main>
  );

  const { voice_7d: v, scoring_30d: s, usage_30d: u, latency_trend: trend } = metrics;

  const trendData = trend.map((d) => ({
    ...d,
    date: d.date.slice(5), // MM-DD
  }));

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav showBack />

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6 animate-fade-in">

        {/* Page header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold gradient-text">Admin Metrics</h1>
            {lastUpdated && (
              <p className="text-xs text-slate-400 mt-1">
                Last updated {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <button
            onClick={fetchMetrics}
            className="btn-secondary flex items-center gap-2 text-sm shrink-0"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Refresh
          </button>
        </div>

        {/* KPI badges */}
        <div className="flex gap-2 flex-wrap">
          <KpiBadge ok={metrics.kpi_latency_ok} label="Latency p95 < 1s" />
          <KpiBadge ok={metrics.kpi_cache_ok} label="Cache > 70%" />
          <KpiBadge ok={metrics.kpi_completion_ok} label="Completion > 60%" />
        </div>

        {/* Voice latency */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700 border-l-2 border-indigo-500 pl-3">
              Voice Pipeline Latency (7-day)
            </h2>
            <span className="text-xs text-slate-400">{v.sample_count} samples</span>
          </div>
          <LatencyRow label="STT" data={v.stt} />
          <LatencyRow label="LLM TTFT" data={v.llm_ttft} />
          <LatencyRow label="TTS" data={v.tts} />
          <LatencyRow label="E2E" data={v.e2e} />
        </div>

        {/* Latency trend chart */}
        {trendData.length > 0 && (
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4 border-l-2 border-indigo-500 pl-3">
              E2E Latency Trend (14-day)
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis unit="ms" tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => `${v}ms`} />
                <ReferenceLine y={1000} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "1000ms target", fontSize: 10, fill: "#ef4444" }} />
                <Line type="monotone" dataKey="e2e_p50" name="p50" stroke="#6366f1" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="e2e_p95" name="p95" stroke="#f59e0b" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-2 justify-center">
              <span className="flex items-center gap-1 text-xs text-slate-500"><span className="w-4 h-0.5 bg-indigo-500 inline-block" /> p50</span>
              <span className="flex items-center gap-1 text-xs text-slate-500"><span className="w-4 h-0.5 bg-amber-400 inline-block" /> p95</span>
              <span className="flex items-center gap-1 text-xs text-slate-500"><span className="w-4 h-0.5 border-t-2 border-dashed border-red-400 inline-block" /> 1000ms DoD</span>
            </div>
          </div>
        )}

        {/* Scoring stats */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3 border-l-2 border-indigo-500 pl-3">
            Scoring Quality (30-day)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard
              label="Avg Score"
              value={s.avg_score !== null ? s.avg_score.toFixed(1) : "—"}
              sub="target: consistent 60+"
            />
            <MetricCard
              label="Score Stddev"
              value={s.score_stddev !== null ? s.score_stddev.toFixed(1) : "—"}
              sub="target: < 8 (DoD)"
              warn={s.score_stddev !== null && s.score_stddev >= 8}
            />
            <MetricCard label="Segments Scored" value={String(s.total_scored)} />
            <MetricCard
              label="Rewind Rate"
              value={`${s.rewind_rate_pct}%`}
              sub="% of segments rewound"
            />
          </div>
        </div>

        {/* Usage + cost */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3 border-l-2 border-indigo-500 pl-3">
            Usage & Cost (30-day)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <MetricCard
              label="Sessions"
              value={String(u.total_sessions)}
              sub={`${u.completed_sessions} completed`}
            />
            <MetricCard
              label="Completion Rate"
              value={`${u.completion_rate_pct}%`}
              sub="target: > 60%"
              warn={u.completion_rate_pct < 60}
            />
            <MetricCard
              label="Total Cost"
              value={`$${u.total_cost_usd.toFixed(3)}`}
              sub={`$${u.cost_per_session_usd.toFixed(4)}/session`}
            />
            <MetricCard
              label="Cache Hit Rate"
              value={`${u.cache_hit_rate_pct}%`}
              sub="Anthropic prompt cache — target: > 70%"
              warn={u.cache_hit_rate_pct < 70 && u.total_api_calls > 0}
            />
            <MetricCard label="API Calls" value={String(u.total_api_calls)} />
          </div>
        </div>

      </div>
    </main>
  );
}
