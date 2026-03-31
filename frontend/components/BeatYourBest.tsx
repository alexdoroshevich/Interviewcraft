"use client";

import { BeatYourBestItem } from "@/lib/api";

const TREND_COLOR = {
  improving: "text-green-600",
  declining: "text-red-500",
  stable: "text-slate-400",
};

interface BeatYourBestProps {
  items: BeatYourBestItem[];
  onChallenge?: (skillName: string) => void;
}

export function BeatYourBest({ items, onChallenge }: BeatYourBestProps) {
  const challengeable = items.filter((i) => i.can_beat).slice(0, 3);
  const mastered = items.filter((i) => !i.can_beat).slice(0, 3);

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-center">
        <p className="text-slate-400 text-sm">
          No records yet. Complete sessions and score them to build your personal bests.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Challenges */}
      {challengeable.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            🎯 Beat Your Best
          </h3>
          <div className="space-y-2">
            {challengeable.map((item) => (
              <div
                key={item.skill_name}
                className="bg-white dark:bg-slate-800 rounded-xl border border-indigo-200 dark:border-indigo-800 p-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0 sm:justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {item.skill_name.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Current: <span className="text-slate-700 dark:text-slate-300 font-mono">{item.current_score}</span>
                    {" · "}
                    Best: <span className="text-indigo-700 dark:text-indigo-400 font-mono font-semibold">{item.best_score}</span>
                    {" · "}
                    Gap: <span className="text-red-500 font-mono">-{item.gap}</span>
                  </p>
                </div>
                {onChallenge && (
                  <button
                    onClick={() => onChallenge(item.skill_name)}
                    className="self-start sm:self-auto px-4 py-2.5 sm:py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors shrink-0 sm:ml-3 min-h-[44px] sm:min-h-0 flex items-center"
                  >
                    Challenge →
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mastered */}
      {mastered.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            ✅ Mastered (at personal best)
          </h3>
          <div className="space-y-2">
            {mastered.map((item) => (
              <div
                key={item.skill_name}
                className="bg-green-50 dark:bg-green-950/30 rounded-xl border border-green-100 dark:border-green-800 px-3 py-3 flex items-center justify-between min-h-[48px]"
              >
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {item.skill_name.replace(/_/g, " ")}
                </p>
                <span className="text-green-700 dark:text-green-400 font-mono text-sm font-semibold ml-3">
                  {item.best_score}/100
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
