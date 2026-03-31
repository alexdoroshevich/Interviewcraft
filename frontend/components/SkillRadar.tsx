"use client";

import { useRef } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { SkillNodeResponse, SkillHistoryPoint } from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildRadarData(nodes: SkillNodeResponse[]) {
  const catMap: Record<string, number[]> = {};
  for (const node of nodes) {
    if (!catMap[node.skill_category]) catMap[node.skill_category] = [];
    catMap[node.skill_category].push(node.current_score);
  }

  const LABELS: Record<string, string> = {
    behavioral: "Behavioral",
    system_design: "System Design",
    communication: "Communication",
    coding_discussion: "Coding",
    negotiation: "Negotiation",
  };

  return Object.entries(catMap).map(([cat, scores]) => ({
    key: cat,
    label: LABELS[cat] ?? cat,
    score: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
  }));
}

// Convert polar to cartesian
function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

// Build SVG polygon points string
function polygonPoints(
  cx: number,
  cy: number,
  maxR: number,
  scores: number[],
  total: number,
) {
  return scores
    .map((score, i) => {
      const angle = (360 / total) * i;
      const r = (score / 100) * maxR;
      const p = polar(cx, cy, r, angle);
      return `${p.x},${p.y}`;
    })
    .join(" ");
}

// Category accent colors
const CAT_COLORS: Record<string, string> = {
  behavioral: "#6366f1",      // indigo
  system_design: "#8b5cf6",   // violet
  communication: "#06b6d4",   // cyan
  coding_discussion: "#10b981", // emerald
  negotiation: "#f59e0b",     // amber
};

// ── Custom SVG Spider Web ──────────────────────────────────────────────────────

interface SkillRadarProps {
  nodes: SkillNodeResponse[];
  activeCategory?: string | null;
  onCategoryClick?: (category: string | null) => void;
}

export function SkillRadar({ nodes, activeCategory, onCategoryClick }: SkillRadarProps) {
  const pathRef = useRef<SVGPolygonElement | null>(null);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
        No skill data yet
      </div>
    );
  }

  const data = buildRadarData(nodes);
  const n = data.length;
  const cx = 200;
  const cy = 200;
  const maxR = 140;
  const rings = [20, 40, 60, 80, 100];

  const scorePoints = polygonPoints(cx, cy, maxR, data.map((d) => d.score), n);
  const outerPoints = polygonPoints(cx, cy, maxR, Array(n).fill(100), n);

  // Colours come from CSS variables defined in globals.css.
  // They update instantly when the `dark` class toggles — no JS needed.
  const bgColor        = "var(--radar-bg)";
  const gridColor      = "var(--radar-grid)";
  const outerGridColor = "var(--radar-outer)";
  const axisColor      = "var(--radar-axis)";
  const labelColor     = "var(--radar-label)";
  const ringLabelColor = "var(--radar-ring-label)";
  const dotStroke      = "var(--radar-dot-stroke)";

  return (
    <div className="relative">
      {/* Glow backdrop — opacity 0.1 so it never blocks the SVG */}
      <div
        className="absolute inset-0 rounded-2xl pointer-events-none"
        style={{ background: "linear-gradient(to bottom right, rgb(99 102 241), rgb(139 92 246), rgb(6 182 212))", opacity: 0.1 }}
      />

      <svg
        viewBox="-80 -30 560 460"
        className="w-full"
        aria-label="Skill spider web chart"
      >
        {/* Explicit background — fill via CSS variable so dark mode is instant */}
        <rect x="-80" y="-30" width="560" height="460" style={{ fill: bgColor }} />

        <defs>
          {/* Gradient fill for the score polygon */}
          <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#818cf8" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.25" />
          </radialGradient>

          {/* Glow filter */}
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Soft drop shadow for the polygon */}
          <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="#6366f1" floodOpacity="0.4" />
          </filter>
        </defs>

        {/* ── Grid rings ──────────────────────────────────────────────────── */}
        {rings.map((pct) => {
          const pts = polygonPoints(cx, cy, maxR, Array(n).fill(pct), n);
          return (
            <polygon
              key={pct}
              points={pts}
              fill="none"
              style={{ stroke: pct === 100 ? outerGridColor : gridColor }}
              strokeWidth={pct === 100 ? 1.5 : 0.75}
              strokeDasharray={pct < 100 ? "3 3" : undefined}
            />
          );
        })}

        {/* Ring labels at 20/40/60/80 on the first axis */}
        {[20, 40, 60, 80].map((pct) => {
          const p = polar(cx, cy, (pct / 100) * maxR, 0);
          return (
            <text
              key={pct}
              x={p.x + 4}
              y={p.y}
              fontSize="9"
              style={{ fill: ringLabelColor }}
              dominantBaseline="middle"
            >
              {pct}
            </text>
          );
        })}

        {/* ── Axis lines ──────────────────────────────────────────────────── */}
        {data.map((d, i) => {
          const angle = (360 / n) * i;
          const outer = polar(cx, cy, maxR, angle);
          return (
            <line
              key={d.key}
              x1={cx}
              y1={cy}
              x2={outer.x}
              y2={outer.y}
              style={{ stroke: axisColor }}
              strokeWidth={0.75}
            />
          );
        })}

        {/* ── Score polygon (filled) ──────────────────────────────────────── */}
        <polygon
          ref={pathRef}
          points={scorePoints}
          fill="url(#radarFill)"
          stroke="#6366f1"
          strokeWidth={2.5}
          strokeLinejoin="round"
          filter="url(#softShadow)"
          style={{ transition: "all 0.6s cubic-bezier(0.34,1.56,0.64,1)" }}
        />

        {/* ── Dots + labels at each axis ──────────────────────────────────── */}
        {data.map((d, i) => {
          const angle = (360 / n) * i;
          const r = (d.score / 100) * maxR;
          const dot = polar(cx, cy, r, angle);
          const labelR = maxR + 28;
          const labelPos = polar(cx, cy, labelR, angle);
          const color = CAT_COLORS[d.key] ?? "#6366f1";

          // Text anchor based on position
          const textAnchor =
            labelPos.x < cx - 5 ? "end" :
            labelPos.x > cx + 5 ? "start" :
            "middle";

          const isActive = !activeCategory || activeCategory === d.key;
          const handleClick = () => onCategoryClick?.(activeCategory === d.key ? null : d.key);

          return (
            <g
              key={d.key}
              onClick={onCategoryClick ? handleClick : undefined}
              style={{ cursor: onCategoryClick ? "pointer" : undefined, opacity: isActive ? 1 : 0.35, transition: "opacity 0.2s" }}
            >
              {/* Score dot */}
              <circle
                cx={dot.x}
                cy={dot.y}
                r={5}
                fill={color}
                style={{ stroke: dotStroke }}
                strokeWidth={2}
                filter="url(#glow)"
              />

              {/* Score value bubble */}
              <g>
                <rect
                  x={dot.x - 14}
                  y={dot.y - 26}
                  width={28}
                  height={16}
                  rx={8}
                  fill={color}
                  opacity={0.9}
                />
                <text
                  x={dot.x}
                  y={dot.y - 15}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="9"
                  fontWeight="700"
                  fill="white"
                >
                  {d.score}
                </text>
              </g>

              {/* Category label — uses accent color, always visible */}
              <text
                x={labelPos.x}
                y={labelPos.y}
                textAnchor={textAnchor}
                dominantBaseline="middle"
                fontSize="11"
                fontWeight="600"
                style={{ fill: color }}
              >
                {d.label}
              </text>
            </g>
          );
        })}

        {/* ── Center dot ──────────────────────────────────────────────────── */}
        <circle cx={cx} cy={cy} r={3} fill="#6366f1" opacity={0.5} />
      </svg>
    </div>
  );
}

// ── Skill sparkline (unchanged logic, same API) ────────────────────────────────

interface SkillSparklineProps {
  history: SkillHistoryPoint[];
  trend: string;
}

export function SkillSparkline({ history, trend }: SkillSparklineProps) {
  if (history.length < 2) {
    return <div className="w-16 h-8 flex items-center justify-center text-xs text-slate-300">—</div>;
  }

  const color =
    trend === "improving" ? "#22c55e" :
    trend === "declining" ? "#ef4444" :
    "#94a3b8";

  const data = history.slice(-8).map((p, i) => ({ i, score: p.score }));

  return (
    <div className="w-16 h-8 shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="score"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Enhanced Skill list ────────────────────────────────────────────────────────

const TREND_ICON: Record<string, string> = {
  improving: "↑",
  declining: "↓",
  stable: "→",
};

const TREND_COLOR: Record<string, string> = {
  improving: "text-emerald-500",
  declining: "text-red-400",
  stable: "text-slate-400",
};

function ScoreRing({ score }: { score: number }) {
  const r = 18;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color =
    score >= 80 ? "#10b981" :
    score >= 60 ? "#f59e0b" :
    "#f43f5e";

  return (
    <svg width="44" height="44" viewBox="0 0 44 44" className="shrink-0">
      <circle cx="22" cy="22" r={r} fill="none" className="stroke-slate-100 dark:stroke-slate-700" strokeWidth="4" />
      <circle
        cx="22"
        cy="22"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="4"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform="rotate(-90 22 22)"
        style={{ transition: "stroke-dasharray 0.5s ease" }}
      />
      <text
        x="22"
        y="22"
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="10"
        fontWeight="700"
        fill={color}
      >
        {score}
      </text>
    </svg>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  behavioral: "border-l-indigo-400",
  system_design: "border-l-violet-400",
  communication: "border-l-cyan-400",
  coding_discussion: "border-l-emerald-400",
  negotiation: "border-l-amber-400",
};

export function SkillList({
  nodes,
  historyMap = {},
}: {
  nodes: SkillNodeResponse[];
  historyMap?: Record<string, SkillHistoryPoint[]>;
}) {
  const CATEGORY_LABELS: Record<string, string> = {
    behavioral: "Behavioral",
    system_design: "System Design",
    communication: "Communication",
    coding_discussion: "Coding",
    negotiation: "Negotiation",
  };

  const grouped: Record<string, SkillNodeResponse[]> = {};
  for (const node of nodes) {
    if (!grouped[node.skill_category]) grouped[node.skill_category] = [];
    grouped[node.skill_category].push(node);
  }

  return (
    <div className="space-y-5">
      {Object.entries(grouped).map(([cat, catNodes]) => {
        const borderColor = CATEGORY_COLORS[cat] ?? "border-l-slate-300";
        const catColor = CAT_COLORS[cat] ?? "#6366f1";

        return (
          <div key={cat}>
            {/* Category header */}
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: catColor }} />
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                {CATEGORY_LABELS[cat] ?? cat}
              </h3>
            </div>

            <div className="space-y-2">
              {catNodes.map((node) => {
                const scoreBg =
                  node.current_score >= 80 ? "bg-emerald-50 dark:bg-emerald-950/20" :
                  node.current_score >= 60 ? "bg-amber-50 dark:bg-amber-950/20" :
                  "bg-rose-50 dark:bg-rose-950/20";

                return (
                  <div
                    key={node.id}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border-l-[3px] ${borderColor} ${scoreBg}
                      border border-slate-100 dark:border-slate-800 transition-all hover:shadow-sm`}
                  >
                    {/* Score ring */}
                    <ScoreRing score={node.current_score} />

                    {/* Skill name + trend */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200 capitalize">
                        {node.skill_name.replace(/_/g, " ")}
                      </p>
                      <p className={`text-xs font-semibold mt-0.5 ${TREND_COLOR[node.trend] ?? "text-slate-400"}`}>
                        {TREND_ICON[node.trend] ?? "→"} {node.trend}
                      </p>
                    </div>

                    {/* Sparkline */}
                    {historyMap[node.skill_name] && (
                      <SkillSparkline
                        history={historyMap[node.skill_name]}
                        trend={node.trend}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
