"use client";

import { useEffect, useState } from "react";
import { api, RewindStartResponse, RewindScoreResponse, ApiError } from "@/lib/api";

// ── Delta display ─────────────────────────────────────────────────────────────

function DeltaDisplay({ result }: { result: RewindScoreResponse }) {
  const deltaColor =
    result.delta > 0 ? "text-green-600" :
    result.delta < 0 ? "text-red-500" :
    "text-slate-500";

  const deltaSign = result.delta > 0 ? "+" : "";

  return (
    <div className="space-y-4">
      {/* Score comparison */}
      <div className="flex items-center justify-center gap-6 py-4">
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">Before</p>
          <p className="text-3xl font-bold text-slate-400">{result.original_score}</p>
        </div>
        <div className="text-center">
          <p className={`text-4xl font-bold ${deltaColor}`}>
            {deltaSign}{result.delta}
          </p>
          <p className="text-xs text-slate-400 mt-1">delta</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">After</p>
          <p className={`text-3xl font-bold ${
            result.new_score >= 80 ? "text-green-600" :
            result.new_score >= 60 ? "text-yellow-600" :
            "text-red-500"
          }`}>{result.new_score}</p>
        </div>
      </div>

      {/* Reason */}
      <div className="bg-slate-50 rounded-lg p-3">
        <p className="text-sm text-slate-700">{result.reason}</p>
      </div>

      {/* Fixed rules */}
      {result.rules_fixed.length > 0 && (
        <div>
          <p className="text-xs font-medium text-green-700 mb-1.5">✅ Fixed</p>
          <div className="space-y-1">
            {result.rules_fixed.map((r) => (
              <span key={r} className="inline-block text-xs bg-green-50 text-green-700 border border-green-200 rounded px-2 py-0.5 mr-1.5">
                {r.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* New issues */}
      {result.rules_new.length > 0 && (
        <div>
          <p className="text-xs font-medium text-red-600 mb-1.5">⚠️ New issues</p>
          <div className="space-y-1">
            {result.rules_new.map((r) => (
              <span key={r} className="inline-block text-xs bg-red-50 text-red-600 border border-red-200 rounded px-2 py-0.5 mr-1.5">
                {r.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Best rewind score */}
      {result.best_rewind_score > result.original_score && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2 text-sm">
          <span className="font-medium text-indigo-800">Personal best this segment: {result.best_rewind_score}</span>
          <span className="text-indigo-600 ml-2">(+{result.best_rewind_score - result.original_score} from original)</span>
        </div>
      )}

      <p className="text-xs text-slate-400 text-center">Rewind #{result.rewind_count}</p>
    </div>
  );
}

// ── Re-answer form ────────────────────────────────────────────────────────────

function ReAnswerForm({
  context,
  sessionId,
  onResult,
}: {
  context: RewindStartResponse;
  sessionId: string;
  onResult: (result: RewindScoreResponse) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!answer.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.rewind.score(sessionId, context.segment_id, answer);
      onResult(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Scoring failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Question */}
      <div className="bg-slate-50 rounded-lg p-3">
        <p className="text-xs text-slate-400 mb-1">Question</p>
        <p className="text-sm font-medium text-slate-800">{context.question}</p>
      </div>

      {/* Hint */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
        <p className="text-xs font-medium text-amber-800 mb-1">💡 This time:</p>
        <p className="text-sm text-amber-700">{context.hint}</p>
      </div>

      {/* Rules to fix */}
      {context.rules_to_fix.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {context.rules_to_fix.map((r) => (
            <span key={r} className="text-xs bg-red-50 text-red-600 border border-red-200 rounded px-2 py-0.5">
              {r.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Answer textarea */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1.5">
          Your re-answer
        </label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={6}
          placeholder="Type your improved answer here..."
          className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
        />
        <p className="text-xs text-slate-400 mt-1 text-right">{answer.length} chars</p>
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading || !answer.trim()}
        className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Scoring…" : "Score My Rewind →"}
      </button>
    </div>
  );
}

// ── Main RewindPanel ──────────────────────────────────────────────────────────

export function RewindPanel({
  sessionId,
  segmentId,
  segmentIndex,
  onClose,
}: {
  sessionId: string;
  segmentId: string;
  segmentIndex: number;
  onClose: () => void;
}) {
  const [phase, setPhase] = useState<"loading" | "form" | "result" | "error">("loading");
  const [context, setContext] = useState<RewindStartResponse | null>(null);
  const [result, setResult] = useState<RewindScoreResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load context on mount
  useEffect(() => {
    api.rewind.start(sessionId, segmentId)
      .then((ctx) => {
        setContext(ctx);
        setPhase("form");
      })
      .catch((e) => {
        setLoadError(e instanceof ApiError ? e.message : "Failed to load rewind context");
        setPhase("error");
      });
  }, [sessionId, segmentId]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div>
            <p className="text-sm font-semibold text-slate-800">
              ↩ Rewind — Segment {segmentIndex + 1}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">Re-answer and see your delta score</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg font-light leading-none"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          {phase === "loading" && (
            <div className="space-y-3 animate-pulse">
              <div className="h-16 bg-slate-100 rounded-lg" />
              <div className="h-24 bg-slate-100 rounded-lg" />
              <div className="h-32 bg-slate-100 rounded-lg" />
            </div>
          )}

          {phase === "error" && (
            <p className="text-sm text-red-600 text-center py-4">{loadError}</p>
          )}

          {phase === "form" && context && (
            <ReAnswerForm
              context={context}
              sessionId={sessionId}
              onResult={(res) => {
                setResult(res);
                setPhase("result");
              }}
            />
          )}

          {phase === "result" && result && (
            <div className="space-y-4">
              <DeltaDisplay result={result} />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setResult(null);
                    setPhase("form");
                  }}
                  className="flex-1 py-2 border border-indigo-300 text-indigo-600 rounded-lg text-sm font-medium hover:bg-indigo-50 transition-colors"
                >
                  Try Again
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
