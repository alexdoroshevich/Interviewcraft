import { tokens } from "@/lib/tokens";
import { AnimatedScore } from "./AnimatedScore";

interface ScoreBenchmarkProps {
  score: number;
  targetLevel?: "L4" | "L5" | "L6";
  animated?: boolean;
}

export function ScoreBenchmark({ score, targetLevel = "L5", animated = true }: ScoreBenchmarkProps) {
  const colors = tokens.scoreColor(score);
  const levels = [tokens.level.l4, tokens.level.l5, tokens.level.l6];

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {animated
        ? <AnimatedScore value={score} className="text-5xl" />
        : <span className={`text-5xl font-black font-mono ${colors.text}`}>{score}</span>
      }
      <div className="flex items-center gap-1.5 flex-wrap">
        {levels.map((lvl) => {
          const passing = score >= lvl.threshold;
          const isTarget = lvl.label === targetLevel;
          return (
            <span
              key={lvl.label}
              className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                passing
                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                  : isTarget
                  ? "bg-rose-50 border-rose-200 text-rose-600"
                  : "bg-slate-50 border-slate-200 text-slate-400"
              }`}
            >
              {lvl.label} {passing ? "✓" : `needs ${lvl.threshold - score}+`}
            </span>
          );
        })}
      </div>
    </div>
  );
}
