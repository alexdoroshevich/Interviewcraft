"use client";

import { useState } from "react";
import { LevelBadge, type LevelAssessment } from "./LevelBadge";
import { RewindPanel } from "./RewindPanel";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface EvidenceSpan {
  start_ms: number;
  end_ms: number;
  server_extracted_quote: string | null;
}

export interface RuleTriggered {
  rule: string;
  confidence: "strong" | "weak";
  evidence: EvidenceSpan;
  fix: string;
  impact: string;
}

export interface CategoryScores {
  structure: number;
  depth: number;
  communication: number;
  seniority_signal: number;
}

export interface SegmentScore {
  id: string;
  session_id: string;
  segment_index: number;
  question_text: string;
  overall_score: number;
  confidence: string;
  category_scores: CategoryScores;
  rules_triggered: RuleTriggered[];
  level_assessment: LevelAssessment;
  diff_versions: DiffVersions | null;
  rewind_count: number;
  best_rewind_score: number | null;
}

export interface DiffVersions {
  minimal: DiffVersion;
  medium: DiffVersion;
  ideal: DiffVersion;
}

export interface DiffVersion {
  text: string;
  changes: Array<{ before: string; after: string; rule: string; impact: string }>;
  estimated_new_score: number;
}

// ── Score ring ─────────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const color =
    score >= 80 ? "text-green-600" :
    score >= 60 ? "text-yellow-600" :
    "text-red-500";

  return (
    <div className={`text-3xl font-bold tabular-nums ${color}`}>
      {score}
      <span className="text-sm font-normal text-slate-400">/100</span>
    </div>
  );
}

// ── Category bar ──────────────────────────────────────────────────────────────

function CategoryBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 80 ? "bg-green-400" :
    score >= 60 ? "bg-yellow-400" :
    "bg-red-400";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-slate-500 shrink-0">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-6 text-right text-slate-600 font-mono">{score}</span>
    </div>
  );
}

// ── Rule row ──────────────────────────────────────────────────────────────────

function RuleRow({ rule }: { rule: RuleTriggered }) {
  const [open, setOpen] = useState(false);

  const formatTs = (ms: number) => {
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return `${m}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="border border-slate-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-slate-50 transition-colors"
      >
        <span className={`mt-0.5 text-xs font-bold shrink-0 px-1.5 py-0.5 rounded ${
          rule.confidence === "strong" ? "bg-red-100 text-red-700" : "bg-yellow-50 text-yellow-700"
        }`}>
          {rule.confidence === "strong" ? "!" : "?"}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-700 truncate">{rule.rule.replace(/_/g, " ")}</p>
          <p className="text-xs text-slate-400 mt-0.5">
            {formatTs(rule.evidence.start_ms)}–{formatTs(rule.evidence.end_ms)}
            {" · "}<span className="text-indigo-600">{rule.impact}</span>
          </p>
        </div>
        <span className="text-slate-300 text-xs mt-1">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-slate-100 pt-2">
          {rule.evidence.server_extracted_quote && (
            <blockquote className="text-xs text-slate-500 italic border-l-2 border-slate-200 pl-2">
              &ldquo;{rule.evidence.server_extracted_quote}&rdquo;
            </blockquote>
          )}
          <div className="flex gap-1.5 items-start">
            <span className="text-xs font-bold text-green-600 shrink-0 mt-0.5">Fix:</span>
            <p className="text-xs text-slate-600">{rule.fix}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function LintCard({ score }: { score: SegmentScore }) {
  const [showRewind, setShowRewind] = useState(false);

  const CATEGORY_LABELS: Record<string, string> = {
    structure: "Structure",
    depth: "Depth",
    communication: "Communication",
    seniority_signal: "Seniority Signal",
  };

  return (
    <>
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-400 uppercase tracking-wide font-medium">
            Segment {score.segment_index + 1}
          </p>
          <p className="text-sm font-medium text-slate-700 mt-0.5 line-clamp-1">
            {score.question_text}
          </p>
          {score.rewind_count > 0 && (
            <p className="text-xs text-indigo-600 mt-0.5">
              ↩ {score.rewind_count} rewind{score.rewind_count !== 1 ? "s" : ""}
              {score.best_rewind_score !== null && ` · best: ${score.best_rewind_score}`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <ScoreRing score={score.overall_score} />
        </div>
      </div>

      {/* Category breakdown */}
      <div className="px-4 py-3 border-b border-slate-100 space-y-1.5">
        {Object.entries(score.category_scores).map(([cat, val]) => (
          <CategoryBar key={cat} label={CATEGORY_LABELS[cat] ?? cat} score={val as number} />
        ))}
      </div>

      {/* Level assessment */}
      <div className="px-4 py-3 border-b border-slate-100">
        <p className="text-xs font-medium text-slate-500 mb-2">Level Assessment</p>
        <LevelBadge assessment={score.level_assessment} />
      </div>

      {/* Rules triggered */}
      <div className="px-4 py-3 border-b border-slate-100">
        {score.rules_triggered.length === 0 ? (
          <p className="text-sm text-green-600 font-medium">✅ No rules triggered — clean answer!</p>
        ) : (
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-500">
              {score.rules_triggered.length} rule{score.rules_triggered.length !== 1 ? "s" : ""} triggered
            </p>
            {score.rules_triggered.map((r, i) => (
              <RuleRow key={i} rule={r} />
            ))}
          </div>
        )}
      </div>

      {/* Coaching: what to improve next time */}
      {(score.level_assessment?.gaps?.length > 0 || score.rules_triggered.length > 0) && (
        <div className="px-4 py-3 border-b border-slate-100 bg-amber-50/40">
          <p className="text-xs font-semibold text-amber-800 mb-2">What to focus on next time</p>
          <ul className="space-y-1.5">
            {/* Level gaps first */}
            {(score.level_assessment?.gaps ?? []).map((gap, i) => (
              <li key={`gap-${i}`} className="flex gap-2 text-xs text-slate-700">
                <span className="text-amber-500 shrink-0 mt-0.5">→</span>
                <span>{gap}</span>
              </li>
            ))}
            {/* Top rule fixes (max 3, strong confidence first) */}
            {[...score.rules_triggered]
              .sort((a, b) => (a.confidence === "strong" ? -1 : 1))
              .slice(0, 3)
              .map((r, i) => (
                <li key={`fix-${i}`} className="flex gap-2 text-xs text-slate-700">
                  <span className="text-indigo-400 shrink-0 mt-0.5">→</span>
                  <span><span className="font-medium text-slate-500">{r.rule.replace(/_/g, " ")}:</span> {r.fix}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Rewind button */}
      <div className="px-4 pb-3 pt-3">
        <button
          onClick={() => setShowRewind(true)}
          className="w-full py-2 border border-indigo-200 text-indigo-600 rounded-lg text-xs font-medium hover:bg-indigo-50 transition-colors"
        >
          ↩ Rewind this segment — re-answer and see delta
        </button>
      </div>
    </div>

    {showRewind && (
      <RewindPanel
        sessionId={score.session_id}
        segmentId={score.id}
        segmentIndex={score.segment_index}
        onClose={() => setShowRewind(false)}
      />
    )}
    </>
  );
}
