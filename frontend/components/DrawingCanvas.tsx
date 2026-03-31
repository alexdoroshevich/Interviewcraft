"use client";

import { useRef, useEffect, useState, useCallback } from "react";

type Tool = "select" | "pen" | "rect" | "ellipse" | "line" | "arrow" | "arrow2" | "cylinder" | "diamond" | "text" | "eraser";

const COLORS = ["#1e293b", "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#0ea5e9", "#94a3b8"];
const STROKE_WIDTHS = [1.5, 3, 6];

interface Shape {
  id: string;
  type: Exclude<Tool, "select" | "eraser" | "pen">;
  x1: number; y1: number; x2: number; y2: number;
  color: string;
  strokeWidth: number;
  text?: string;
}

interface PenStroke {
  id: string;
  type: "pen";
  points: Array<{ x: number; y: number }>;
  color: string;
  strokeWidth: number;
}

export type DrawItem = Shape | PenStroke;

function uid() { return Math.random().toString(36).slice(2); }

function drawShape(ctx: CanvasRenderingContext2D, shape: Shape) {
  ctx.strokeStyle = shape.color;
  ctx.lineWidth = shape.strokeWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  const { x1, y1, x2, y2 } = shape;
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2;
  const rx = Math.abs(x2 - x1) / 2;
  const ry = Math.abs(y2 - y1) / 2;

  ctx.beginPath();
  switch (shape.type) {
    case "rect":
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      break;
    case "ellipse":
      ctx.ellipse(cx, cy, Math.max(rx, 1), Math.max(ry, 1), 0, 0, 2 * Math.PI);
      ctx.stroke();
      break;
    case "line":
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      break;
    case "arrow": {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const head = 14;
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - head * Math.cos(angle - 0.4), y2 - head * Math.sin(angle - 0.4));
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - head * Math.cos(angle + 0.4), y2 - head * Math.sin(angle + 0.4));
      ctx.stroke();
      break;
    }
    case "arrow2": {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const head = 14;
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      // Forward head
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - head * Math.cos(angle - 0.4), y2 - head * Math.sin(angle - 0.4));
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - head * Math.cos(angle + 0.4), y2 - head * Math.sin(angle + 0.4));
      ctx.stroke();
      // Backward head
      const angle2 = angle + Math.PI;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x1 - head * Math.cos(angle2 - 0.4), y1 - head * Math.sin(angle2 - 0.4));
      ctx.moveTo(x1, y1);
      ctx.lineTo(x1 - head * Math.cos(angle2 + 0.4), y1 - head * Math.sin(angle2 + 0.4));
      ctx.stroke();
      break;
    }
    case "cylinder": {
      const eRy = Math.max(ry * 0.25, 8);
      // Body
      ctx.beginPath();
      ctx.moveTo(x1, y1 + eRy);
      ctx.lineTo(x1, y2 - eRy);
      ctx.ellipse(cx, y2 - eRy, rx, eRy, 0, 0, Math.PI);
      ctx.lineTo(x2, y1 + eRy);
      ctx.ellipse(cx, y1 + eRy, rx, eRy, 0, Math.PI, 0);
      ctx.stroke();
      // Top cap
      ctx.beginPath();
      ctx.ellipse(cx, y1 + eRy, rx, eRy, 0, 0, 2 * Math.PI);
      ctx.stroke();
      break;
    }
    case "diamond": {
      ctx.moveTo(cx, y1);
      ctx.lineTo(x2, cy);
      ctx.lineTo(cx, y2);
      ctx.lineTo(x1, cy);
      ctx.closePath();
      ctx.stroke();
      break;
    }
    case "text":
      ctx.font = `${Math.max(shape.strokeWidth * 6, 14)}px Inter, sans-serif`;
      ctx.fillStyle = shape.color;
      ctx.fillText(shape.text ?? "", x1, y1);
      break;
  }

  // Selection indicator
  if ((shape as Shape & { selected?: boolean }).selected) {
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.strokeRect(x1 - 4, y1 - 4, (x2 - x1) + 8, (y2 - y1) + 8);
    ctx.setLineDash([]);
  }
}

function drawPen(ctx: CanvasRenderingContext2D, stroke: PenStroke) {
  if (stroke.points.length < 2) return;
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.strokeWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  stroke.points.forEach((p) => ctx.lineTo(p.x, p.y));
  ctx.stroke();
}

function redraw(canvas: HTMLCanvasElement, items: DrawItem[], preview?: DrawItem | null) {
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  items.forEach((item) => {
    if (item.type === "pen") drawPen(ctx, item);
    else drawShape(ctx, item as Shape);
  });
  if (preview) {
    if (preview.type === "pen") drawPen(ctx, preview);
    else drawShape(ctx, preview as Shape);
  }
}

interface DrawingCanvasProps {
  onItemsChange?: (items: DrawItem[]) => void;
}

export function DrawingCanvas({ onItemsChange }: DrawingCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tool, setTool] = useState<Tool>("rect");
  const [color, setColor] = useState(COLORS[0]);
  const [strokeWidth, setStrokeWidth] = useState(STROKE_WIDTHS[0]);
  const [items, setItems] = useState<DrawItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [textInput, setTextInput] = useState<{ canvasX: number; canvasY: number } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const isDrawing = useRef(false);
  const startPos = useRef<{ x: number; y: number } | null>(null);
  const currentPen = useRef<PenStroke | null>(null);
  const dragOffset = useRef<{ dx: number; dy: number } | null>(null);

  // Resize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      canvas.width = Math.floor(width);
      canvas.height = Math.floor(height);
      redraw(canvas, items);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    return () => ro.disconnect();
  }, [items]);

  // Re-render when items change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) redraw(canvas, items);
  }, [items]);

  // Notify parent of board changes (debounced 800ms) so the AI interviewer
  // can update its context without flooding on every mouse-move.
  useEffect(() => {
    if (!onItemsChange) return;
    const timer = setTimeout(() => onItemsChange(items), 800);
    return () => clearTimeout(timer);
  }, [items, onItemsChange]);

  function getPos(e: React.PointerEvent<HTMLCanvasElement>): { x: number; y: number } | null {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function hitTest(pos: { x: number; y: number }): DrawItem | null {
    for (let i = items.length - 1; i >= 0; i--) {
      const item = items[i];
      if (item.type === "pen") continue;
      const s = item as Shape;
      const margin = 8;
      if (pos.x >= Math.min(s.x1, s.x2) - margin &&
          pos.x <= Math.max(s.x1, s.x2) + margin &&
          pos.y >= Math.min(s.y1, s.y2) - margin &&
          pos.y <= Math.max(s.y1, s.y2) + margin) {
        return item;
      }
    }
    return null;
  }

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    const pos = getPos(e);
    if (!pos) return;

    // Capture pointer so events continue even if mouse leaves canvas
    e.currentTarget.setPointerCapture(e.pointerId);

    if (tool === "select") {
      const hit = hitTest(pos);
      setSelectedId(hit?.id ?? null);
      if (hit && hit.type !== "pen") {
        const s = hit as Shape;
        dragOffset.current = { dx: pos.x - s.x1, dy: pos.y - s.y1 };
      }
      isDrawing.current = !!hit;
      startPos.current = pos;
      return;
    }

    if (tool === "eraser") {
      const hit = hitTest(pos);
      if (hit) setItems((prev) => prev.filter((i) => i.id !== hit.id));
      return;
    }

    if (tool === "text") {
      setTextInput({ canvasX: pos.x, canvasY: pos.y });
      return;
    }

    isDrawing.current = true;
    startPos.current = pos;

    if (tool === "pen") {
      currentPen.current = { id: uid(), type: "pen", points: [pos], color, strokeWidth };
    }
  }, [tool, color, strokeWidth, items]); // eslint-disable-line react-hooks/exhaustive-deps

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawing.current) return;
    const start = startPos.current;
    if (!start) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const pos = getPos(e);
    if (!pos) return;

    if (tool === "select") {
      const offset = dragOffset.current;
      if (selectedId && offset) {
        setItems((prev) => prev.map((item) => {
          if (item.id !== selectedId || item.type === "pen") return item;
          const s = item as Shape;
          const w = s.x2 - s.x1;
          const h = s.y2 - s.y1;
          const nx1 = pos.x - offset.dx;
          const ny1 = pos.y - offset.dy;
          return { ...s, x1: nx1, y1: ny1, x2: nx1 + w, y2: ny1 + h };
        }));
      }
      return;
    }

    if (tool === "pen" && currentPen.current) {
      currentPen.current.points.push(pos);
      redraw(canvas, items, currentPen.current);
      return;
    }

    // Shape preview
    const preview: Shape = {
      id: "_preview",
      type: tool as Shape["type"],
      x1: start.x, y1: start.y,
      x2: pos.x, y2: pos.y,
      color, strokeWidth,
    };
    redraw(canvas, items, preview);
  }, [tool, color, strokeWidth, items, selectedId]);

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    const start = startPos.current;
    startPos.current = null;

    const pos = getPos(e);

    if (tool === "pen" && currentPen.current) {
      setItems((prev) => [...prev, currentPen.current!]);
      currentPen.current = null;
      return;
    }

    if (tool === "select") {
      dragOffset.current = null;
      return;
    }

    if (!start || !pos) return;

    if (["rect","ellipse","line","arrow","arrow2","cylinder","diamond"].includes(tool)) {
      const dx = Math.abs(pos.x - start.x);
      const dy = Math.abs(pos.y - start.y);
      if (dx < 4 && dy < 4) return; // too small, ignore
      setItems((prev) => [...prev, {
        id: uid(),
        type: tool as Shape["type"],
        x1: start.x, y1: start.y,
        x2: pos.x, y2: pos.y,
        color, strokeWidth,
      }]);
    }
  }, [tool, color, strokeWidth]);

  function undo() {
    setItems((prev) => prev.slice(0, -1));
    setSelectedId(null);
  }

  function clear() {
    setItems([]);
    setSelectedId(null);
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") undo();
      if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedId) {
          setItems((prev) => prev.filter((i) => i.id !== selectedId));
          setSelectedId(null);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedId]);

  const TOOLS: { id: Tool; icon: string; label: string }[] = [
    { id: "select",   icon: "↖",  label: "Select / Move" },
    { id: "pen",      icon: "✏",  label: "Pen" },
    { id: "rect",     icon: "□",  label: "Rectangle" },
    { id: "ellipse",  icon: "○",  label: "Ellipse / Circle" },
    { id: "line",     icon: "╱",  label: "Line" },
    { id: "arrow",    icon: "→",  label: "Arrow →" },
    { id: "arrow2",   icon: "↔",  label: "Bidirectional ↔" },
    { id: "cylinder", icon: "⊡",  label: "Database / Cylinder" },
    { id: "diamond",  icon: "◇",  label: "Diamond" },
    { id: "text",     icon: "T",  label: "Text Label" },
    { id: "eraser",   icon: "⌫",  label: "Eraser" },
  ];

  const fontSize = Math.max(strokeWidth * 6, 14);

  function commitText(value: string) {
    if (value.trim() && textInput) {
      setItems((prev) => [...prev, {
        id: uid(), type: "text" as const,
        x1: textInput.canvasX, y1: textInput.canvasY,
        x2: textInput.canvasX + value.length * (fontSize * 0.6), y2: textInput.canvasY + fontSize,
        color, strokeWidth, text: value.trim(),
      }]);
    }
    setTextInput(null);
  }

  return (
    <div className={isFullscreen
      ? "fixed inset-0 z-50 flex flex-col bg-white dark:bg-slate-950"
      : "flex flex-col h-full bg-white dark:bg-slate-950"
    }>
      {/* Toolbar */}
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-700 px-2 py-2 space-y-2">
        {/* Tool buttons */}
        <div className="flex flex-wrap gap-1">
          {TOOLS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTool(t.id)}
              title={t.label}
              className={`w-9 h-9 sm:w-8 sm:h-8 text-sm rounded-lg flex items-center justify-center transition-colors ${
                tool === t.id
                  ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 ring-1 ring-indigo-400"
                  : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              {t.icon}
            </button>
          ))}
        </div>

        {/* Colors + stroke + actions */}
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                title={c}
                className={`w-7 h-7 sm:w-5 sm:h-5 rounded-full border-2 transition-all ${color === c ? "border-indigo-500 scale-110" : "border-transparent hover:border-slate-300"}`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <div className="flex gap-1 ml-1">
            {STROKE_WIDTHS.map((w) => (
              <button
                key={w}
                onClick={() => setStrokeWidth(w)}
                className={`w-8 h-8 sm:w-6 sm:h-6 rounded flex items-center justify-center transition-colors ${strokeWidth === w ? "bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"}`}
              >
                <div className="rounded-full bg-current" style={{ width: w * 1.5 + 2, height: w * 1.5 + 2 }} />
              </button>
            ))}
          </div>
          <div className="flex gap-1 ml-auto">
            <button onClick={undo} className="text-xs px-3 py-2 sm:px-2 sm:py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors min-h-[36px]" title="Undo (Ctrl+Z)">↩</button>
            <button onClick={clear} className="text-xs px-3 py-2 sm:px-2 sm:py-1 rounded bg-red-50 dark:bg-red-900/20 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors min-h-[36px]">Clear</button>
            <button
              onClick={() => setIsFullscreen((f) => !f)}
              className="text-xs px-3 py-2 sm:px-2 sm:py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors min-h-[36px]"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? "⊠" : "⛶"}
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden bg-white dark:bg-slate-950">
        {/* Dot grid */}
        <div className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(circle, #94a3b820 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0"
          style={{ cursor: tool === "select" ? "default" : tool === "eraser" ? "cell" : "crosshair", touchAction: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />
        {/* Inline text input */}
        {textInput && (
          <input
            autoFocus
            type="text"
            className="absolute bg-transparent border-b-2 border-indigo-400 outline-none min-w-[80px] px-0 leading-none"
            style={{
              left: textInput.canvasX,
              top: textInput.canvasY - fontSize,
              fontSize: `${fontSize}px`,
              color,
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") { commitText(e.currentTarget.value); }
              if (e.key === "Escape") { setTextInput(null); }
            }}
            onBlur={(e) => commitText(e.currentTarget.value)}
          />
        )}

        {/* Tool hint */}
        <div className="absolute bottom-2 left-2 text-[10px] text-slate-400 pointer-events-none select-none">
          {TOOLS.find(t => t.id === tool)?.label}
          {tool === "select" && selectedId ? " · Del to remove" : ""}
          {tool === "text" ? " · click to place label" : ""}
          {isFullscreen ? " · ⊠ to exit fullscreen" : ""}
        </div>
      </div>
    </div>
  );
}
