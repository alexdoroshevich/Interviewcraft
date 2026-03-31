"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ShareCardPublicResponse, ApiError } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  behavioral: "#6366f1",
  system_design: "#8b5cf6",
  communication: "#06b6d4",
  coding_discussion: "#10b981",
  negotiation: "#f59e0b",
};

function ReadinessRing({ score }: { score: number }) {
  const r = 54;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score / 100);
  const color = score >= 70 ? "#6366f1" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#e2e8f0" strokeWidth="12" />
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{score}</div>
        <div className="text-xs text-slate-500">readiness</div>
      </div>
    </div>
  );
}

export default function SharePage({ params }: { params: { token: string } }) {
  const [card, setCard] = useState<ShareCardPublicResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.share
      .getCard(params.token)
      .then(setCard)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Card not found"))
      .finally(() => setLoading(false));
  }, [params.token]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-violet-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
      </main>
    );
  }

  if (error || !card) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-violet-50 flex items-center justify-center p-4">
        <div className="text-center max-w-sm">
          <div className="text-5xl mb-4">🔗</div>
          <h1 className="text-xl font-bold text-slate-800 mb-2">Link not found</h1>
          <p className="text-slate-500 text-sm mb-6">
            This share link may have expired or been removed.
          </p>
          <Link href="/" className="inline-block px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors">
            Try InterviewCraft →
          </Link>
        </div>
      </main>
    );
  }

  const { snapshot } = card;
  const categories = Object.entries(snapshot.skill_scores_by_category).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-violet-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-5">
          <div className="flex items-center gap-2 mb-1">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
            <span className="text-white font-semibold text-sm">InterviewCraft</span>
          </div>
          <p className="text-indigo-100 text-xs">Interview Readiness Report</p>
        </div>

        {/* Readiness ring + stats */}
        <div className="px-6 py-6 flex items-center gap-6 border-b border-slate-100">
          <ReadinessRing score={snapshot.readiness_score} />
          <div className="space-y-2">
            <div>
              <p className="text-xs text-slate-400">Avg skill score</p>
              <p className="text-lg font-bold text-indigo-600">{snapshot.avg_skill_score}/100</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Sessions completed</p>
              <p className="text-lg font-bold text-slate-700">{snapshot.session_count}</p>
            </div>
          </div>
        </div>

        {/* Top strengths */}
        {snapshot.top_strengths.length > 0 && (
          <div className="px-6 py-4 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Top Strengths</p>
            <div className="flex flex-wrap gap-2">
              {snapshot.top_strengths.map((s) => (
                <span key={s} className="text-xs px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full font-medium">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Category bars */}
        {categories.length > 0 && (
          <div className="px-6 py-4 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Skill Categories</p>
            <div className="space-y-2.5">
              {categories.map(([cat, score]) => (
                <div key={cat}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600 capitalize">{cat.replace(/_/g, " ")}</span>
                    <span className="font-mono text-slate-500">{score}</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${score}%`,
                        backgroundColor: CATEGORY_COLORS[cat] ?? "#6366f1",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer CTA */}
        <div className="px-6 py-5 bg-slate-50 text-center">
          <p className="text-xs text-slate-400 mb-3">
            Generated {new Date(snapshot.generated_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
          </p>
          <Link
            href="/"
            className="inline-block px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors"
          >
            Try InterviewCraft →
          </Link>
        </div>
      </div>
    </main>
  );
}
