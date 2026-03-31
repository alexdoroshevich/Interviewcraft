// Single source of truth for score colours and level thresholds.
// Import these — never use raw Tailwind strings in logic.

export const tokens = {
  score: {
    excellent: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-200', hex: '#10b981' },
    good:      { bg: 'bg-amber-100',   text: 'text-amber-700',   border: 'border-amber-200',   hex: '#f59e0b' },
    weak:      { bg: 'bg-rose-100',    text: 'text-rose-600',    border: 'border-rose-200',    hex: '#f43f5e' },
  },
  level: {
    l4: { label: 'L4', color: 'text-slate-500',  threshold: 60 },
    l5: { label: 'L5', color: 'text-indigo-600', threshold: 75 },
    l6: { label: 'L6', color: 'text-violet-600', threshold: 88 },
  },
  scoreColor: (score: number) =>
    score >= 80 ? tokens.score.excellent :
    score >= 60 ? tokens.score.good :
    tokens.score.weak,
} as const;
