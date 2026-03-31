"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, SessionResponse, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

// ── Helpers ────────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  behavioral: "Behavioral",
  system_design: "System Design",
  coding_discussion: "Coding",
  negotiation: "Negotiation",
  diagnostic: "Diagnostic",
  debrief: "Debrief",
};

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  completed: "bg-slate-100 text-slate-600",
  abandoned: "bg-red-50 text-red-500",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  completed: "Completed",
  abandoned: "Abandoned",
};

const PROFILE_LABELS: Record<string, string> = {
  quality: "Quality",
  balanced: "Balanced",
  budget: "Budget",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(created: string, ended: string | null) {
  if (!ended) return "—";
  const ms = new Date(ended).getTime() - new Date(created).getTime();
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

// ── Session type SVG icons ─────────────────────────────────────────────────────

function TypeIcon({ type }: { type: string }) {
  const cls = "w-5 h-5 text-indigo-400 shrink-0";
  switch (type) {
    case "behavioral":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
        </svg>
      );
    case "system_design":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      );
    case "negotiation":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 3" />
          <path d="M9 3.5C9 3.5 7 6 7 9" />
        </svg>
      );
    case "diagnostic":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      );
    default:
      // coding_discussion and fallback
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      );
  }
}

// ── Onboarding banner ─────────────────────────────────────────────────────────

function OnboardingBanner() {
  return (
    <div className="bg-gradient-to-r from-indigo-50 to-violet-50 border border-indigo-200 rounded-xl p-5 mb-6">
      <h2 className="font-semibold text-indigo-900 mb-1">Welcome to InterviewCraft!</h2>
      <p className="text-indigo-700 text-sm mb-3">
        Your first session will be a 5-minute diagnostic so I can build your personalized
        training plan. Ready?
      </p>
      <Link href="/sessions/new" className="btn-primary inline-block text-sm">
        Start Diagnostic (5 min)
      </Link>
    </div>
  );
}

// ── Session row ───────────────────────────────────────────────────────────────

function SessionRow({ session, onDelete }: { session: SessionResponse; onDelete: (id: string) => void }) {
  const [confirming, setConfirming] = useState(false);

  const href =
    session.status === "active"
      ? `/sessions/${session.id}`
      : `/sessions/${session.id}/transcript`;
  const canDelete = session.status !== "active";
  const isCompleted = session.status === "completed";
  const isActive = session.status === "active";

  return (
    <div className="card-hover rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 transition-all">
      <div className="flex items-center gap-2">
        <Link
          href={href}
          className="flex-1 flex items-center justify-between p-4 group"
        >
          <div className="flex items-center gap-3">
            <TypeIcon type={session.type} />
            <div>
              <div className="font-medium text-slate-900 dark:text-slate-100 text-sm">
                {TYPE_LABELS[session.type] ?? session.type}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">{formatDate(session.created_at)}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-right">
            <div className="hidden sm:block text-xs text-slate-400">
              {formatDuration(session.created_at, session.ended_at)}
            </div>
            {parseFloat(session.total_cost_usd) > 0 && (
              <div className="hidden sm:block text-xs font-mono text-slate-400">
                ${parseFloat(session.total_cost_usd).toFixed(3)}
              </div>
            )}
            {/* B2: Single Next Action */}
            {isActive && (
              <Badge className="bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400 border-transparent hover:bg-green-200 dark:hover:bg-green-900/60">
                Resume →
              </Badge>
            )}
            {isCompleted && (
              <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-400 border-transparent group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                Score &amp; Review →
              </Badge>
            )}
            {!isActive && !isCompleted && (
              <Badge variant="outline" className={`${STATUS_STYLES[session.status] ?? ""}`}>
                {STATUS_LABELS[session.status] ?? session.status}
              </Badge>
            )}
          </div>
        </Link>

        {canDelete && !confirming && (
          <button
            onClick={() => setConfirming(true)}
            className="p-2.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0 mr-1"
            aria-label="Delete session"
            title="Delete session"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        )}
      </div>

      {confirming && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-red-50 border-t border-red-100 rounded-b-xl">
          <span className="text-xs text-red-700 font-medium">Delete this session? This cannot be undone.</span>
          <div className="flex gap-2">
            <button
              onClick={() => { setConfirming(false); onDelete(session.id); }}
              className="text-xs px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors font-medium"
            >
              Yes, delete
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="text-xs px-3 py-1 bg-white border border-slate-200 text-slate-600 rounded-md hover:bg-slate-50 transition-colors font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SessionsPage() {
  const { ready } = useAuth();
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    api.sessions
      .list(50)
      .then(setSessions)
      .catch((e) => {
        const msg = e instanceof ApiError ? e.message : "Failed to load sessions";
        setFetchError(msg);
        toast.error(msg);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  async function handleDelete(id: string) {
    try {
      await api.sessions.delete(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to delete session");
    }
  }

  const isFirstTime = !loading && sessions.length === 0 && !fetchError;

  // B4: Streak — consecutive calendar days with at least one completed session
  const streak = useMemo(() => {
    const days = new Set(
      sessions
        .filter((s) => s.status === "completed")
        .map((s) => new Date(s.created_at).toDateString())
    );
    let count = 0;
    const today = new Date();
    for (let i = 0; i < 365; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      if (days.has(d.toDateString())) { count++; } else if (i > 0) { break; }
    }
    return count;
  }, [sessions]);

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />

      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Onboarding */}
        {isFirstTime && <OnboardingBanner />}

        {/* Error */}
        {fetchError && (
          <div className="text-red-600 text-sm mb-4 p-3 bg-red-50 rounded-lg">
            {fetchError}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        )}

        {/* Sessions list */}
        {!loading && sessions.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                Sessions ({sessions.length})
              </h1>
              {/* B4: Streak */}
              {streak > 0 && (
                <div className="flex items-center gap-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-full px-3 py-1">
                  <span className="text-base" role="img" aria-label="fire">🔥</span>
                  <span className="text-xs font-bold text-amber-700 dark:text-amber-400">{streak} day streak</span>
                </div>
              )}
            </div>
            <div className="space-y-2 animate-fade-in">
              {sessions.map((s) => (
                <SessionRow key={s.id} session={s} onDelete={handleDelete} />
              ))}
            </div>
          </>
        )}

        {/* Empty state — no sessions yet */}
        {!loading && sessions.length === 0 && !fetchError && !isFirstTime && (
          <EmptyState
            icon={
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            }
            title="No sessions yet"
            description="Start your first interview session to begin building your skill graph."
            action={{ label: "Start a Session", href: "/sessions/new" }}
          />
        )}

        {/* Error state */}
        {!loading && sessions.length === 0 && fetchError && (
          <EmptyState
            icon={
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            }
            title="Failed to load sessions"
            description="Please refresh the page. If the problem persists, check your connection."
          />
        )}
      </div>
    </main>
  );
}
