/**
 * Utilities for describing board items and code content to the AI interviewer.
 *
 * The AI receives these descriptions alongside each voice turn so it can
 * react to what the candidate has drawn or written — just like a real
 * interviewer watching a shared screen.
 */

// Local types that structurally match DrawingCanvas's DrawItem union.
// TypeScript structural typing ensures compatibility without a circular import.

type ShapeType =
  | "rect" | "ellipse" | "line" | "arrow" | "arrow2"
  | "cylinder" | "diamond" | "text";

interface ShapeItem {
  id: string;
  type: ShapeType;
  x1: number; y1: number; x2: number; y2: number;
  color: string;
  strokeWidth: number;
  text?: string;
}

interface PenItem {
  id: string;
  type: "pen";
  points: Array<{ x: number; y: number }>;
  color: string;
  strokeWidth: number;
}

export type DrawItem = ShapeItem | PenItem;

// ── Helpers ───────────────────────────────────────────────────────────────────

const SHAPE_NAMES: Partial<Record<ShapeType, string>> = {
  rect:     "rectangle",
  ellipse:  "circle/ellipse",
  cylinder: "database (cylinder)",
  diamond:  "decision diamond",
  line:     "line",
  arrow:    "arrow",
  arrow2:   "bidirectional arrow",
  text:     "text label",
};

function centerOf(s: ShapeItem) {
  return { x: (s.x1 + s.x2) / 2, y: (s.y1 + s.y2) / 2 };
}

function dist(ax: number, ay: number, bx: number, by: number) {
  return Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2);
}

function gridPos(
  cx: number,
  cy: number,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
): string {
  const w = bounds.maxX - bounds.minX || 1;
  const h = bounds.maxY - bounds.minY || 1;
  const rx = (cx - bounds.minX) / w;
  const ry = (cy - bounds.minY) / h;
  const col = rx < 0.33 ? "left" : rx < 0.67 ? "center" : "right";
  const row = ry < 0.33 ? "top"  : ry < 0.67 ? "middle" : "bottom";
  if (col === "center" && row === "middle") return "center";
  if (col === "center") return row;
  if (row === "middle") return col;
  return `${row}-${col}`;
}

// ── Board description ─────────────────────────────────────────────────────────

/**
 * Convert the canvas DrawItem[] into a human-readable description
 * the LLM can reason about. Returns null if the board is empty.
 */
export function describeBoardItems(items: DrawItem[]): string | null {
  if (items.length === 0) return null;

  const shapes  = items.filter((i): i is ShapeItem => i.type !== "pen");
  const pens    = items.filter((i) => i.type === "pen");

  if (shapes.length === 0) {
    // Only freehand strokes — not useful to describe in detail
    return `[CANDIDATE'S DESIGN BOARD]\nContains ${pens.length} freehand drawing stroke${pens.length > 1 ? "s" : ""}.\n\nNote: you can see their whiteboard just as a real interviewer would.`;
  }

  // Components (non-arrow, non-line shapes)
  const components = shapes.filter(
    (s) => !["arrow", "arrow2", "line"].includes(s.type) && s.type !== "text",
  );
  const arrows     = shapes.filter((s) => ["arrow", "arrow2"].includes(s.type));
  const textLabels = shapes.filter((s) => s.type === "text" && s.text?.trim());

  // Bounding box for relative positioning
  const allCenters = components.map(centerOf);
  const bounds = allCenters.length
    ? {
        minX: Math.min(...allCenters.map((c) => c.x)),
        maxX: Math.max(...allCenters.map((c) => c.x)),
        minY: Math.min(...allCenters.map((c) => c.y)),
        maxY: Math.max(...allCenters.map((c) => c.y)),
      }
    : { minX: 0, maxX: 800, minY: 0, maxY: 500 };

  const lines: string[] = ["[CANDIDATE'S DESIGN BOARD]"];

  // ── Components ──
  if (components.length > 0) {
    lines.push("Components:");
    for (const s of components) {
      const c   = centerOf(s);
      const pos = gridPos(c.x, c.y, bounds);
      const lbl = s.text?.trim() ? ` "${s.text.trim()}"` : "";
      lines.push(`  • ${SHAPE_NAMES[s.type] ?? s.type}${lbl} — ${pos}`);
    }
  }

  // ── Connections (arrows) ──
  if (arrows.length > 0) {
    const CONNECT_PX = 120; // distance threshold to consider arrow attached to a shape
    lines.push("Connections:");
    for (const arrow of arrows) {
      const nearest = (px: number, py: number) => {
        const hit = components
          .map((c) => ({ c, d: dist(px, py, centerOf(c).x, centerOf(c).y) }))
          .sort((a, b) => a.d - b.d)[0];
        if (!hit || hit.d > CONNECT_PX) return null;
        return hit.c.text?.trim() ? `"${hit.c.text.trim()}"` : (SHAPE_NAMES[hit.c.type] ?? hit.c.type);
      };

      const from = nearest(arrow.x1, arrow.y1);
      const to   = nearest(arrow.x2, arrow.y2);
      const lbl  = arrow.text?.trim() ? ` [${arrow.text.trim()}]` : "";
      const sym  = arrow.type === "arrow2" ? "↔" : "→";

      if (from && to) {
        lines.push(`  • ${from} ${sym} ${to}${lbl}`);
      } else {
        lines.push(`  • ${SHAPE_NAMES[arrow.type] ?? "arrow"}${lbl}`);
      }
    }
  }

  // ── Free text labels ──
  if (textLabels.length > 0) {
    lines.push("Text annotations:");
    for (const t of textLabels) {
      lines.push(`  • "${t.text!.trim()}"`);
    }
  }

  if (pens.length > 0) {
    lines.push(`  (+ ${pens.length} freehand stroke${pens.length > 1 ? "s" : ""})`);
  }

  lines.push(
    "\nYou can see their design board in real time, exactly as a real interviewer would. " +
    "React naturally — ask about missing components, scalability, failure modes, trade-offs. " +
    "Do NOT recite this description back; just reference what you observe naturally in conversation.",
  );

  return lines.join("\n");
}

// ── Code description ──────────────────────────────────────────────────────────

/**
 * Format the code editor contents into a context block for the LLM.
 * Returns empty string if the editor is empty.
 */
export function describeCode(
  code: string,
  language: string,
  lastOutput?: string,
): string {
  const trimmed = code.trim();
  if (!trimmed) return "";

  const lines: string[] = [
    `[CANDIDATE'S CODE EDITOR — ${language.toUpperCase()}]`,
    "```" + language,
    trimmed,
    "```",
  ];

  if (lastOutput && lastOutput.trim() && lastOutput !== "(no output)") {
    lines.push(`Last run output:\n${lastOutput.trim().slice(0, 400)}`);
  }

  lines.push(
    "\nYou can see their code editor in real time, exactly as a real interviewer would. " +
    "React naturally — comment on their approach, time/space complexity, edge cases, or style. " +
    "Do NOT copy-paste their code back verbatim.",
  );

  return lines.join("\n");
}
