"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api, NegotiationHistoryItem, NegotiationStartRequest, NegotiationStartResponse, ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color = score >= 70 ? "bg-green-400" : score >= 50 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-32 text-slate-500 shrink-0">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-6 text-right text-slate-600 font-mono">{score}</span>
    </div>
  );
}

// ── History card ──────────────────────────────────────────────────────────────

function HistoryCard({ item }: { item: NegotiationHistoryItem }) {
  return (
    <Link href={`/sessions/${item.session_id}/transcript`}
      className="block card-hover p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">{item.company}</p>
          <p className="text-xs text-slate-500">{item.role} · {item.level}</p>
          <p className="text-xs text-slate-400 mt-0.5">
            Offer: ${item.offer_amount.toLocaleString()} ·{" "}
            {new Date(item.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-xl font-bold font-mono ${
            item.overall_score >= 70 ? "text-green-600" :
            item.overall_score >= 50 ? "text-yellow-600" : "text-red-500"
          }`}>{item.overall_score || "—"}</p>
          {item.money_left_on_table > 0 && (
            <p className="text-xs text-red-500 mt-0.5">
              ${item.money_left_on_table.toLocaleString()} left
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}

// ── Start form ────────────────────────────────────────────────────────────────

function StartForm({ onStarted }: { onStarted: (res: NegotiationStartResponse) => void }) {
  const [form, setForm] = useState<NegotiationStartRequest>({
    company: "", role: "Senior Software Engineer", level: "L5",
    offer_amount: 0, market_rate: 0, quality_profile: "balanced",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof NegotiationStartRequest, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function handleStart() {
    if (!form.company || !form.offer_amount || !form.market_rate) return;
    setLoading(true); setError(null);
    try {
      const res = await api.negotiation.start(form);
      onStarted(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card p-4 space-y-4">
      <h2 className="text-sm font-semibold text-slate-800">Setup Negotiation Practice</h2>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Company</label>
          <input value={form.company} onChange={(e) => set("company", e.target.value)}
            placeholder="Google, Meta, Amazon…"
            className="input-field" />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Level</label>
          <select value={form.level} onChange={(e) => set("level", e.target.value)}
            className="input-field">
            {["L4", "L5", "L6", "Senior", "Staff", "Principal"].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Their Offer ($)</label>
          <input type="number" value={form.offer_amount || ""}
            onChange={(e) => set("offer_amount", parseInt(e.target.value) || 0)}
            placeholder="200000"
            className="input-field" />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Your Market Rate ($)</label>
          <input type="number" value={form.market_rate || ""}
            onChange={(e) => set("market_rate", parseInt(e.target.value) || 0)}
            placeholder="230000"
            className="input-field" />
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
        <strong>How it works:</strong> The AI will play a recruiter with a hidden max budget (15% above the offer).
        Score is based on anchoring, value articulation, counter-strategy, and emotional control.
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <button onClick={handleStart}
        disabled={loading || !form.company || !form.offer_amount || !form.market_rate}
        className="w-full btn-primary">
        {loading ? "Starting…" : "Start Negotiation Session →"}
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NegotiationPage() {
  const { ready } = useAuth();
  const [history, setHistory] = useState<NegotiationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [started, setStarted] = useState<NegotiationStartResponse | null>(null);

  useEffect(() => {
    if (!ready) return;
    api.negotiation.history()
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [ready]);

  if (started) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-violet-50 flex items-center justify-center p-4">
        <div className="card p-6 max-w-md w-full text-center space-y-4 animate-fade-in">
          <div className="flex items-center justify-center w-14 h-14 mx-auto rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 shadow-lg shadow-indigo-200">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-800">Session Created!</h2>
          <p className="text-sm text-slate-600">
            Your negotiation session with <strong>{started.company}</strong> is ready.
            Start the voice session to practice.
          </p>
          <Link
            href={`/sessions/${started.session_id}`}
            className="block w-full btn-primary"
          >
            Go to Session →
          </Link>
          <button onClick={() => setStarted(null)}
            className="text-xs text-slate-400 hover:text-slate-600">
            Set up another
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
        <StartForm onStarted={setStarted} />

        {!loading && history.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 border-l-2 border-indigo-500 pl-3">
              Past Sessions
            </h2>
            <div className="space-y-3">
              {history.map((item) => <HistoryCard key={item.session_id} item={item} />)}
            </div>
          </div>
        )}

        {!loading && history.length === 0 && (
          <p className="text-center text-slate-400 text-sm py-4">
            No past negotiation sessions. Start one above to practice.
          </p>
        )}
      </div>
    </main>
  );
}
