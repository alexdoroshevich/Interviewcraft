"use client";

// ── Types ──────────────────────────────────────────────────────────────────────

export type LevelResult = "pass" | "borderline" | "fail";

export interface LevelAssessment {
  l4: LevelResult;
  l5: LevelResult;
  l6: LevelResult;
  gaps: string[];
}

// ── Badge styles ───────────────────────────────────────────────────────────────

const RESULT_META: Record<LevelResult, { icon: string; color: string; label: string }> = {
  pass:       { icon: "✅", color: "text-green-700",  label: "Pass"       },
  borderline: { icon: "⚠️", color: "text-yellow-700", label: "Borderline" },
  fail:       { icon: "❌", color: "text-red-600",    label: "Fail"       },
};

// ── Component ─────────────────────────────────────────────────────────────────

export function LevelBadge({ assessment }: { assessment: LevelAssessment }) {
  const levels: [string, LevelResult][] = [
    ["L4", assessment.l4],
    ["L5", assessment.l5],
    ["L6", assessment.l6],
  ];

  return (
    <div className="space-y-2">
      <div className="flex gap-3 flex-wrap">
        {levels.map(([level, result]) => {
          const meta = RESULT_META[result];
          return (
            <span
              key={level}
              className={`inline-flex items-center gap-1 text-sm font-medium px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 ${meta.color}`}
            >
              <span>{meta.icon}</span>
              <span>{level}</span>
              <span className="font-normal text-xs opacity-70">{meta.label}</span>
            </span>
          );
        })}
      </div>

      {assessment.gaps.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-slate-500 mb-1">To reach next level:</p>
          <ul className="space-y-0.5">
            {assessment.gaps.map((gap, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                <span className="text-slate-300 mt-0.5">→</span>
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
