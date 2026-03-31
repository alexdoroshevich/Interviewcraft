interface DeltaBadgeProps {
  delta: number;
  showArrow?: boolean;
  className?: string;
}

export function DeltaBadge({ delta, showArrow = true, className = "" }: DeltaBadgeProps) {
  const positive = delta > 0;
  const zero = delta === 0;

  const bg    = positive ? "bg-emerald-100 text-emerald-700" : zero ? "bg-slate-100 text-slate-600" : "bg-rose-100 text-rose-600";
  const arrow = positive ? "↑" : zero ? "→" : "↓";
  const sign  = positive ? "+" : "";

  return (
    <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-semibold font-mono ${bg} ${className}`}>
      {showArrow && <span>{arrow}</span>}
      {sign}{delta} pts
    </span>
  );
}
