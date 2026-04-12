"use client";

import { useState, useRef, useCallback } from "react";
import type { DiffVersions, DiffVersion } from "./LintCard";
import { getToken } from "@/lib/api";

// ── Signal-to-noise highlighting ──────────────────────────────────────────────
// Signal words (facts, numbers, actions) are bright; noise (filler, hedging) is dimmed.

const NOISE_PATTERNS = [
  /\b(um|uh|like|basically|sort of|you know|i guess|kind of|maybe|perhaps|just|very|really|quite|actually|honestly|literally|you see|right\?|okay so)\b/i,
  /\b(improved|better|faster|good|nice|great|thing|stuff|some|several)\b/i,
];

const SIGNAL_PATTERNS = [
  /\b\d[\d.,]*\s*(%|ms|s|k|M|B|x|KB|MB|GB|TB|QPS|RPS|USD|\$|hrs?|days?|weeks?|months?)\b/i,
  /\b(designed|built|reduced|increased|migrated|deployed|implemented|led|owned|mentored|saved|shipped|fixed|resolved|achieved)\b/i,
  /\$[\d,]+/,
  /\b\d+[\d,]*\b/,
];

function isNoise(word: string): boolean {
  return NOISE_PATTERNS.some((p) => p.test(word.toLowerCase()));
}

function isSignal(word: string): boolean {
  return SIGNAL_PATTERNS.some((p) => p.test(word));
}

function HighlightedText({ text }: { text: string }) {
  const tokens = text.split(/(\s+)/);
  return (
    <span>
      {tokens.map((token, i) => {
        if (/^\s+$/.test(token)) return <span key={i}>{token}</span>;
        const signal = isSignal(token);
        const noise = !signal && isNoise(token);
        return (
          <span
            key={i}
            className={signal ? "font-semibold text-slate-900" : noise ? "text-slate-300" : ""}
          >
            {token}
          </span>
        );
      })}
    </span>
  );
}

// ── Version tabs ──────────────────────────────────────────────────────────────

type VersionKey = "minimal" | "medium" | "ideal";

const VERSION_META: Record<VersionKey, { label: string; desc: string; color: string }> = {
  minimal: { label: "Minimal Patch", desc: "Fix 1-2 sentences",       color: "text-blue-600" },
  medium:  { label: "Medium Rewrite", desc: "Restructure + fix all",   color: "text-purple-600" },
  ideal:   { label: "Ideal Answer",   desc: "L5/L6 level",             color: "text-green-600" },
};

// ── Change annotation ─────────────────────────────────────────────────────────

function ChangeAnnotation({ change }: {
  change: { before: string; after: string; rule: string; impact: string };
}) {
  return (
    <div className="text-xs font-mono border border-slate-200 rounded-lg overflow-hidden">
      {change.before && (
        <div className="px-2 py-1 bg-red-50 border-b border-red-100">
          <span className="text-red-500 mr-1.5">−</span>
          <span className="text-red-800">{change.before}</span>
        </div>
      )}
      <div className="px-2 py-1 bg-green-50">
        <span className="text-green-500 mr-1.5">+</span>
        <span className="text-green-800">{change.after}</span>
        <span className="ml-2 text-slate-400">[+{change.rule.replace(/_/g, " ")} → {change.impact}]</span>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface DiffViewProps {
  originalScore: number;
  diffVersions: DiffVersions;
  originalAnswer?: string;
  sessionId?: string;
  segmentIndex?: number;
}

export function DiffView({ originalScore, diffVersions, originalAnswer, sessionId, segmentIndex }: DiffViewProps) {
  const [activeVersion, setActiveVersion] = useState<VersionKey>("minimal");
  const [showSignalNoise, setShowSignalNoise] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playIdealAnswer = useCallback(async () => {
    if (!sessionId || segmentIndex === undefined) return;
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }

    setLoadingAudio(true);
    try {
      const token = getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
      const res = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/scores/${segmentIndex}/play-ideal`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );
      if (!res.ok) throw new Error("Failed to generate audio");
      const data = await res.json();

      const binary = atob(data.audio_data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { setPlaying(false); URL.revokeObjectURL(url); };
      audio.play();
      setPlaying(true);
    } catch {
      setPlaying(false);
    } finally {
      setLoadingAudio(false);
    }
  }, [sessionId, segmentIndex, playing]);

  const version: DiffVersion | undefined = diffVersions[activeVersion] ?? diffVersions["minimal"] ?? Object.values(diffVersions)[0];

  if (!version) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-sm text-slate-400">
        Diff data unavailable.
      </div>
    );
  }

  const gain = version.estimated_new_score - originalScore;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Answer Diff</h3>
        <button
          onClick={() => setShowSignalNoise(!showSignalNoise)}
          className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
            showSignalNoise
              ? "border-indigo-300 bg-indigo-50 text-indigo-700"
              : "border-slate-200 text-slate-500 hover:border-slate-300"
          }`}
        >
          {showSignalNoise ? "Signal/Noise ON" : "Signal/Noise"}
        </button>
      </div>

      {/* Version tabs */}
      <div className="flex border-b border-slate-100">
        {(Object.entries(VERSION_META) as [VersionKey, typeof VERSION_META[VersionKey]][]).map(([key, meta]) => {
          const v = diffVersions[key];
          if (!v) return null;
          const vGain = v.estimated_new_score - originalScore;
          return (
            <button
              key={key}
              onClick={() => setActiveVersion(key)}
              className={`flex-1 px-3 py-2.5 text-left text-xs transition-colors border-b-2 ${
                activeVersion === key
                  ? `border-indigo-500 bg-indigo-50`
                  : "border-transparent hover:bg-slate-50"
              }`}
            >
              <p className={`font-semibold ${activeVersion === key ? "text-indigo-700" : "text-slate-600"}`}>
                {meta.label}
              </p>
              <p className="text-slate-400 mt-0.5">{meta.desc}</p>
              <p className={`mt-0.5 font-mono font-bold text-xs ${meta.color}`}>
                {vGain >= 0 ? "+" : ""}{vGain} pts → {v.estimated_new_score}
              </p>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Score gain banner */}
        <div className={`flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg ${
          gain >= 20 ? "bg-green-50 text-green-700" :
          gain >= 10 ? "bg-blue-50 text-blue-700" :
          "bg-slate-50 text-slate-600"
        }`}>
          <span>{gain >= 0 ? "📈" : "📉"}</span>
          <span>
            {originalScore} → {version.estimated_new_score}
            {gain !== 0 && <span className="font-normal opacity-70"> ({gain >= 0 ? "+" : ""}{gain} points)</span>}
          </span>
        </div>

        {/* Rewritten text */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs font-medium text-slate-400">
              {VERSION_META[activeVersion].label}
            </p>
            {activeVersion === "ideal" && sessionId && segmentIndex !== undefined && (
              <button
                onClick={playIdealAnswer}
                disabled={loadingAudio}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:from-indigo-600 hover:to-violet-600 transition-all disabled:opacity-50"
              >
                {loadingAudio ? (
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : playing ? (
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="4" width="4" height="16" rx="1" />
                    <rect x="14" y="4" width="4" height="16" rx="1" />
                  </svg>
                ) : (
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
                {loadingAudio ? "Generating..." : playing ? "Pause" : "Listen"}
              </button>
            )}
          </div>
          <div className="text-sm text-slate-700 leading-relaxed p-3 bg-slate-50 rounded-lg">
            {showSignalNoise
              ? <HighlightedText text={version.text} />
              : version.text
            }
          </div>
          {showSignalNoise && (
            <p className="text-xs text-slate-400 mt-1">
              <span className="font-semibold text-slate-700">Bold</span> = signal (facts/numbers/actions) ·{" "}
              <span className="text-slate-300">Gray</span> = noise (filler/hedging)
            </p>
          )}
        </div>

        {/* Annotated changes */}
        {version.changes.length > 0 && (
          <div>
            <p className="text-xs font-medium text-slate-400 mb-1.5">What changed</p>
            <div className="space-y-2">
              {version.changes.map((c, i) => (
                <ChangeAnnotation key={i} change={c} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
