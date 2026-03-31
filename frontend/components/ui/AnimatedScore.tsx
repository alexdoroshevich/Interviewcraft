"use client";

import { useEffect, useRef, useState } from "react";
import { tokens } from "@/lib/tokens";

interface AnimatedScoreProps {
  value: number;
  className?: string;
  duration?: number;
}

export function AnimatedScore({ value, className = "", duration = 800 }: AnimatedScoreProps) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef<number | null>(null);
  const colors = tokens.scoreColor(value);

  useEffect(() => {
    const start = performance.now();
    const from = 0;

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (value - from) * eased));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    }

    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [value, duration]);

  return (
    <span
      className={`font-black font-mono tabular-nums ${colors.text} ${className}`}
      role="img"
      aria-label={`Score: ${value} out of 100`}
    >
      {display}
    </span>
  );
}
