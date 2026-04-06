"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import {
  api,
  SessionDetail,
  TranscriptTurn,
  SegmentScoreResponse,
  ScoringStatusResponse,
  SessionMetricsResponse,
  DeliveryAnalysisResponse,
  ApiError,
} from "@/lib/api";
import { AppNav } from "@/components/AppNav";
import { LintCard } from "@/components/LintCard";
import { DiffView } from "@/components/DiffView";
import { ScoreBenchmark } from "@/components/ui/ScoreBenchmark";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

// ── Helpers ────────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  behavioral: "Behavioral", system_design: "System Design",
  coding_discussion: "Coding", negotiation: "Negotiation",
  diagnostic: "Diagnostic", debrief: "Post-Interview Debrief",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatDuration(created: string, ended: string | null) {
  if (!ended) return "—";
  const ms = new Date(ended).getTime() - new Date(created).getTime();
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

function formatTimestamp(ms: number) {
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ── Transcript turn ───────────────────────────────────────────────────────────

function TurnRow({ turn }: { turn: TranscriptTurn }) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex gap-3 py-3 border-b border-border last:border-0 ${isUser ? "flex-row-reverse" : ""}`}>
      <span className="text-xs font-mono text-muted-foreground mt-1 shrink-0 w-10 text-right">
        {formatTimestamp(turn.ts_ms)}
      </span>
      <div className={`flex-1 flex gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
        <span className={`text-xs font-bold mt-1 shrink-0 ${isUser ? "text-indigo-500" : "text-muted-foreground"}`}>
          {isUser ? "You" : "AI"}
        </span>
        <div
          className={`max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-100 rounded-2xl rounded-tr-md"
              : "bg-card border border-border text-card-foreground rounded-2xl rounded-tl-md shadow-sm"
          }`}
        >
          {turn.content}
        </div>
      </div>
    </div>
  );
}

// ── Scoring trigger panel ─────────────────────────────────────────────────────

function ScoringPanel({
  sessionId,
  onScored,
}: {
  sessionId: string;
  onScored: (result: ScoringStatusResponse) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScore() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.scoring.score(sessionId);
      onScored(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Scoring failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="border-indigo-200 bg-indigo-50 dark:bg-indigo-950/30 dark:border-indigo-800 mt-4">
      <CardContent className="py-4">
        {loading ? (
          <div>
            <p className="text-sm font-semibold text-indigo-900 dark:text-indigo-200 mb-3">
              Analyzing your answers... This may take up to a minute.
            </p>
            <Progress value={0} className="h-2 animate-pulse" />
          </div>
        ) : (
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-indigo-900 dark:text-indigo-200">Ready to score this session</p>
              <p className="text-xs text-indigo-700 dark:text-indigo-400 mt-0.5">
                Get lint results, 3 diff versions, and level assessment for each answer.
              </p>
              {error && (
                <Alert variant="destructive" className="mt-2">
                  <AlertDescription className="text-xs">{error}</AlertDescription>
                </Alert>
              )}
            </div>
            <button
              onClick={handleScore}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              Score Session
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Suggested answer card ─────────────────────────────────────────────────────

function SuggestedAnswer({ question, idealText, estimatedScore, changes }: {
  question: string;
  idealText: string;
  estimatedScore: number;
  changes: Array<{ before: string; after: string; rule: string; impact: string }>;
}) {
  const [copied, setCopied] = useState(false);
  const [showFull, setShowFull] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(idealText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-xl overflow-hidden dark:bg-emerald-950/20 dark:border-emerald-800/40">
      <div className="px-4 py-3 border-b border-emerald-200/60 dark:border-emerald-800/40 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-emerald-600 text-base">✦</span>
          <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-300">
            What to add to your answer
          </p>
        </div>
        <span className="text-xs text-emerald-700 dark:text-emerald-400 font-mono font-medium bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 rounded-full shrink-0">
          {estimatedScore > 0 ? `→ ~${estimatedScore}/100` : "ideal"}
        </span>
      </div>

      {changes.length > 0 && (
        <div className="px-4 py-3 border-b border-emerald-200/60 dark:border-emerald-800/40">
          <p className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 mb-2 uppercase tracking-wide">
            Specific gaps in your answer
          </p>
          <ul className="space-y-2">
            {changes.map((c, i) => (
              <li key={i} className="flex gap-2 text-xs">
                <span className="text-emerald-500 shrink-0 mt-0.5 font-bold">+</span>
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {c.rule.replace(/_/g, " ")}
                  </span>
                  {c.before && (
                    <span className="text-muted-foreground ml-1">
                      (you said: &ldquo;{c.before.slice(0, 60)}{c.before.length > 60 ? "…" : ""}&rdquo;)
                    </span>
                  )}
                  <span className="block text-slate-600 dark:text-slate-400 mt-0.5">{c.after}</span>
                  <span className="text-indigo-500 text-[11px] font-medium">{c.impact}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-4 py-3">
        <button
          onClick={() => setShowFull(!showFull)}
          className="text-xs font-medium text-emerald-700 dark:text-emerald-400 hover:text-emerald-900 dark:hover:text-emerald-200 transition-colors w-full text-left flex items-center justify-between"
        >
          <span>{showFull ? "▲ Hide full ideal answer" : "▼ Show full ideal answer"}</span>
          <span className="text-muted-foreground text-[11px]">Q: {question.slice(0, 60)}{question.length > 60 ? "…" : ""}</span>
        </button>
        {showFull && (
          <div className="mt-3">
            <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap bg-card rounded-lg p-3 border border-emerald-200/60 dark:border-emerald-800/30">
              {idealText}
            </p>
            <button
              onClick={handleCopy}
              className="mt-2 text-xs text-emerald-700 dark:text-emerald-400 hover:text-emerald-900 font-medium transition-colors"
            >
              {copied ? "✓ Copied" : "Copy ideal answer"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Latency metrics panel ─────────────────────────────────────────────────────

function LatencyPanel({ m }: { m: SessionMetricsResponse }) {
  if (m.turns === 0) return null;

  const ms = (v: number | null) => v == null ? "—" : `${v}ms`;
  const color = (v: number | null) =>
    v == null ? "text-muted-foreground" :
    v < 1500 ? "text-emerald-600 dark:text-emerald-400" :
    v < 2500 ? "text-amber-600 dark:text-amber-400" :
    "text-rose-500";

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Voice Latency — {m.turns} turn{m.turns !== 1 ? "s" : ""}
          </p>
          <span className={`text-xs font-mono font-bold ${color(m.e2e_p95_ms)}`}>
            p95 {ms(m.e2e_p95_ms)}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          {[
            { label: "E2E avg",  val: m.e2e_avg_ms },
            { label: "E2E p50",  val: m.e2e_p50_ms },
            { label: "STT avg",  val: m.stt_avg_ms },
            { label: "LLM ttft", val: m.llm_avg_ms },
          ].map(({ label, val }) => (
            <div key={label} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-2.5 border border-border">
              <p className={`text-base font-bold font-mono ${color(val)}`}>{ms(val)}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Score summary (top-level overview) ───────────────────────────────────────

function StarRating({ score }: { score: number }) {
  const stars = Math.round(score / 20);
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <svg key={s} className={`w-5 h-5 ${s <= stars ? "text-amber-400" : "text-slate-200 dark:text-slate-700"}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  );
}

function ScoreSummary({ scores }: { scores: SegmentScoreResponse[] }) {
  const avg = Math.round(scores.reduce((s, r) => s + r.overall_score, 0) / scores.length);

  const allGaps: string[] = scores.flatMap((s) =>
    (s.diff_versions?.ideal?.changes ?? []).map((c) => c.rule.replace(/_/g, " "))
  );
  const gapCounts: Record<string, number> = {};
  for (const g of allGaps) gapCounts[g] = (gapCounts[g] ?? 0) + 1;
  const topGaps = Object.entries(gapCounts).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([g]) => g);

  const scoreBg = avg >= 80
    ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/40"
    : avg >= 60
    ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/40"
    : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800/40";

  return (
    <div className={`rounded-2xl border p-5 ${scoreBg}`}>
      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">Session Results</p>
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <ScoreBenchmark score={avg} targetLevel="L5" />
        <div>
          <StarRating score={avg} />
          <p className="text-xs text-muted-foreground mt-1">{scores.length} question{scores.length !== 1 ? "s" : ""} analyzed</p>
        </div>
      </div>
      {topGaps.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Top areas to improve:</p>
          <div className="flex flex-wrap gap-2">
            {topGaps.map((g) => (
              <Badge key={g} variant="outline" className="text-xs capitalize bg-white/70 dark:bg-slate-800/60">
                {g}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Question card (one per scored segment) ────────────────────────────────────

function QuestionCard({ score, index, sessionId }: { score: SegmentScoreResponse; index: number; sessionId: string }) {
  const [showAnswer, setShowAnswer] = useState(false);
  const [showLint, setShowLint] = useState(false);
  const [showDiff, setShowDiff] = useState(true);

  const ideal = score.diff_versions?.ideal;
  const hasDiff = !!(score.diff_versions && (score.diff_versions.minimal || score.diff_versions.medium || score.diff_versions.ideal));
  const scoreColor = score.overall_score >= 80 ? "text-emerald-600 dark:text-emerald-400" : score.overall_score >= 60 ? "text-amber-600 dark:text-amber-400" : "text-rose-500";
  const scoreBadgeBg = score.overall_score >= 80 ? "bg-emerald-100 dark:bg-emerald-900/40" : score.overall_score >= 60 ? "bg-amber-100 dark:bg-amber-900/40" : "bg-rose-100 dark:bg-rose-900/40";

  return (
    <Card>
      <CardContent className="py-4 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <span className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
              Q{index + 1}
            </span>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 leading-snug">
              {score.question_text}
            </p>
          </div>
          <span className={`shrink-0 text-sm font-bold font-mono px-2.5 py-1 rounded-full ${scoreColor} ${scoreBadgeBg}`}>
            {score.overall_score}/100
          </span>
        </div>

        {score.answer_text && (
          <div className="bg-slate-50 dark:bg-slate-800/50 border border-border rounded-xl overflow-hidden">
            <button
              onClick={() => setShowAnswer(!showAnswer)}
              className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 text-xs font-bold flex items-center justify-center">Y</span>
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Your answer</span>
              </div>
              <span className="text-xs text-muted-foreground">{showAnswer ? "▲ Hide" : "▼ Show"}</span>
            </button>
            {showAnswer && (
              <div className="px-4 pb-4 pt-1">
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap bg-card rounded-lg p-3 border border-border">
                  {score.answer_text}
                </p>
              </div>
            )}
          </div>
        )}

        {ideal && (
          <SuggestedAnswer
            question={score.question_text}
            idealText={ideal.text}
            estimatedScore={ideal.estimated_new_score}
            changes={ideal.changes}
          />
        )}

        <div className="flex gap-4 pt-1">
          <button onClick={() => setShowLint(!showLint)} className="text-xs text-muted-foreground hover:text-indigo-600 font-medium transition-colors">
            {showLint ? "▲ Hide" : "▼ Rule analysis"}
          </button>
          <button onClick={() => setShowDiff(!showDiff)} className="text-xs text-muted-foreground hover:text-indigo-600 font-medium transition-colors">
            {showDiff ? "▲ Hide" : "▼ 3 rewrite versions"}
          </button>
        </div>
        {showLint && <LintCard score={score} />}
        {showDiff && (
          hasDiff
            ? <DiffView
                originalScore={score.overall_score}
                diffVersions={score.diff_versions!}
                originalAnswer={score.answer_text}
                sessionId={sessionId}
                segmentIndex={score.segment_index}
              />
            : <div className="text-xs text-muted-foreground bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-border">
                Rewrite versions were not generated for this answer. Try re-scoring the session.
              </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Delivery Analysis Card ────────────────────────────────────────────────────

const FILLER_LABELS: Record<string, string> = {
  um_uh: "um / uh", like: "like", you_know: "you know",
  basically: "basically", literally: "literally", so: "so",
  actually: "actually", right: "right", kind_of: "kind of", sort_of: "sort of",
};

function DeliveryCard({ data }: { data: DeliveryAnalysisResponse }) {
  const scoreColor =
    data.delivery_score >= 90 ? "text-emerald-600 dark:text-emerald-400" :
    data.delivery_score >= 75 ? "text-indigo-600 dark:text-indigo-400" :
    data.delivery_score >= 60 ? "text-amber-600 dark:text-amber-400" :
    "text-red-500";

  const ringColor =
    data.delivery_score >= 90 ? "#10b981" :
    data.delivery_score >= 75 ? "#6366f1" :
    data.delivery_score >= 60 ? "#f59e0b" :
    "#f43f5e";

  const circ = 2 * Math.PI * 18;
  const dash = (data.delivery_score / 100) * circ;

  return (
    <Card>
      <CardContent className="py-4">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4 border-l-2 border-indigo-500 pl-3">
          Voice Delivery Analysis
          {!data.has_word_timestamps && (
            <span className="ml-2 text-xs font-normal text-slate-400">(estimated — word timestamps expired)</span>
          )}
        </h2>

        <div className="flex flex-wrap gap-4 items-start">
          {/* Delivery score ring */}
          <div className="flex flex-col items-center gap-1">
            <svg width="52" height="52" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" className="stroke-slate-100 dark:stroke-slate-700" strokeWidth="4" />
              <circle cx="22" cy="22" r="18" fill="none" stroke={ringColor} strokeWidth="4"
                strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
                transform="rotate(-90 22 22)" style={{ transition: "stroke-dasharray 0.5s ease" }} />
              <text x="22" y="22" textAnchor="middle" dominantBaseline="middle" fontSize="10" fontWeight="700" fill={ringColor}>
                {data.delivery_score}
              </text>
            </svg>
            <p className={`text-xs font-semibold ${scoreColor}`}>{data.delivery_grade}</p>
          </div>

          {/* Key metrics */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 flex-1">
            <div>
              <p className="text-xs text-muted-foreground">Speaking pace</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{data.wpm.toFixed(0)} WPM</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total words</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{data.total_words}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Filler words</p>
              <p className={`text-sm font-semibold ${data.filler_count > 0 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                {data.filler_count} ({(data.filler_rate * 100).toFixed(1)}%)
              </p>
            </div>
            {data.has_word_timestamps && (
              <div>
                <p className="text-xs text-muted-foreground">Long pauses</p>
                <p className={`text-sm font-semibold ${data.long_pause_count > 3 ? "text-amber-600 dark:text-amber-400" : "text-slate-700 dark:text-slate-300"}`}>
                  {data.long_pause_count}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Filler breakdown */}
        {Object.keys(data.fillers_by_type).length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Filler Breakdown</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(data.fillers_by_type)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <span key={type} className="px-2 py-1 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 text-xs rounded-lg font-medium">
                    &quot;{FILLER_LABELS[type] ?? type}&quot; × {count}
                  </span>
                ))}
            </div>
          </div>
        )}

        {/* Coaching tips */}
        <div className="mt-4 space-y-1.5">
          {data.coaching_tips.map((tip, i) => (
            <p key={i} className="text-xs text-slate-600 dark:text-slate-400 flex gap-2">
              <span className="text-indigo-400 shrink-0">→</span>
              {tip}
            </p>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function TranscriptPage() {
  const { ready } = useAuth();
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [scores, setScores] = useState<SegmentScoreResponse[]>([]);
  const [metrics, setMetrics] = useState<SessionMetricsResponse | null>(null);
  const [delivery, setDelivery] = useState<DeliveryAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      api.sessions.get(id),
      api.scoring.getScores(id).catch(() => [] as SegmentScoreResponse[]),
      api.sessions.metrics(id).catch(() => null),
      api.scoring.getDelivery(id).catch(() => null),
    ])
      .then(([sess, scoreList, metricsData, deliveryData]) => {
        setSession(sess);
        setScores(scoreList);
        setMetrics(metricsData);
        setDelivery(deliveryData);
      })
      .catch((e) => setFetchError(e instanceof ApiError ? e.message : "Failed to load session"))
      .finally(() => setLoading(false));
  }, [id, ready]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <AppNav showBack />
        <div className="max-w-2xl mx-auto px-4 py-6 space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 rounded-xl" />)}
        </div>
      </main>
    );
  }

  if (fetchError || !session) {
    return (
      <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Alert variant="destructive" className="max-w-sm">
            <AlertDescription>{fetchError ?? "Session not found"}</AlertDescription>
          </Alert>
          <Link href="/sessions" className="text-indigo-600 hover:text-indigo-700 hover:underline text-sm">← Back to sessions</Link>
        </div>
      </main>
    );
  }

  const turns = (session.transcript ?? []) as TranscriptTurn[];
  const isScored = scores.length > 0;
  const canScore = session.status === "completed" && turns.length > 0 && !isScored;

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav showBack />

      <div className="max-w-2xl mx-auto px-4 py-6 animate-fade-in">
        {/* Session meta */}
        <Card className="mb-6">
          <CardContent className="py-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {TYPE_LABELS[session.type] ?? session.type} Interview
                </h1>
                <p className="text-sm text-muted-foreground mt-0.5">{formatDate(session.created_at)}</p>
              </div>
              <Badge variant={session.status === "active" ? "default" : "secondary"} className="capitalize">
                {session.status}
              </Badge>
            </div>

            <div className="flex gap-6 text-sm text-muted-foreground flex-wrap">
              <span>
                <span className="font-medium text-slate-700 dark:text-slate-300">Duration</span>{" "}
                {formatDuration(session.created_at, session.ended_at)}
              </span>
              <span>
                <span className="font-medium text-slate-700 dark:text-slate-300">Profile</span>{" "}
                {session.quality_profile}
              </span>
              {parseFloat(session.total_cost_usd) > 0 && (
                <span>
                  <span className="font-medium text-slate-700 dark:text-slate-300">Cost</span>{" "}
                  <span className="font-mono">${parseFloat(session.total_cost_usd).toFixed(3)}</span>
                </span>
              )}
              <span>
                <span className="font-medium text-slate-700 dark:text-slate-300">Turns</span>{" "}
                {turns.length}
              </span>
              {isScored && (
                <span>
                  <span className="font-medium text-slate-700 dark:text-slate-300">Avg Score</span>{" "}
                  <span className="font-mono text-indigo-700 dark:text-indigo-400">
                    {Math.round(scores.reduce((s, r) => s + r.overall_score, 0) / scores.length)}
                  </span>
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {canScore && (
          <ScoringPanel
            sessionId={id}
            onScored={(result) => setScores(result.scores)}
          />
        )}

        {delivery && delivery.total_words > 0 && (
          <div className="mt-4">
            <DeliveryCard data={delivery} />
          </div>
        )}

        {isScored && (
          <div className="mt-6 space-y-4">
            <ScoreSummary scores={scores} />

            {/* Download coaching report */}
            <div className="flex flex-col gap-1.5">
              <button
                onClick={async () => {
                  setReportLoading(true);
                  setReportError(null);
                  try {
                    await api.sessions.downloadReport(id);
                  } catch (e) {
                    setReportError(e instanceof Error ? e.message : "Report generation failed. Try again.");
                  } finally {
                    setReportLoading(false);
                  }
                }}
                disabled={reportLoading}
                className="btn-secondary flex items-center justify-center gap-2 text-sm py-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {reportLoading ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-indigo-500" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Generating PDF report… (up to 2 min)
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download Coaching Report (PDF)
                  </>
                )}
              </button>
              {reportError && (
                <p className="text-xs text-rose-500 text-center">{reportError}</p>
              )}
            </div>

            {metrics && <LatencyPanel m={metrics} />}
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest pl-1 pt-2">
              Question-by-question breakdown
            </h2>
            {scores.map((score, i) => (
              <QuestionCard key={score.id} score={score} index={i} sessionId={id} />
            ))}
          </div>
        )}

        {/* Contribute prompt — shown after scoring */}
        {isScored && (
          <div className="mt-4 flex items-center justify-between gap-3 px-4 py-3 bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 rounded-xl">
            <p className="text-sm text-indigo-800 dark:text-indigo-200">
              Encountered a question not in our bank?
            </p>
            <a
              href="/questions/contribute"
              className="shrink-0 text-xs font-semibold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-200 hover:underline"
            >
              Add it →
            </a>
          </div>
        )}

        {/* Transcript */}
        <Card className="mt-6">
          <CardContent className="py-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">Transcript</h2>
            {turns.length === 0 ? (
              <p className="text-muted-foreground text-sm text-center py-8">
                No transcript saved for this session.
              </p>
            ) : (
              <div>
                {turns.map((turn, i) => <TurnRow key={i} turn={turn} />)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
