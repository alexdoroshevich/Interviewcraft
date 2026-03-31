"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useVoiceSession, SessionState, TranscriptEntry } from "@/lib/useVoiceSession";
import { api, SessionResponse } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { DrawingCanvas } from "@/components/DrawingCanvas";
import { CodeNotebook } from "@/components/CodeNotebook";
import { describeBoardItems, describeCode, DrawItem } from "@/lib/contextDescription";

// ── Interview type tools config ─────────────────────────────────────────────

interface ToolItem {
  icon: string;
  label: string;
  tip: string;
  prompt: string;
}

const INTERVIEW_TOOLS: Record<string, { title: string; tools: ToolItem[] }> = {
  behavioral: {
    title: "STAR Framework",
    tools: [
      { icon: "S", label: "Situation", tip: "Set the context — When? Where? What project?", prompt: "Let me set the situation: " },
      { icon: "T", label: "Task", tip: "What was your responsibility or challenge?", prompt: "My task/responsibility was: " },
      { icon: "A", label: "Action", tip: "What did YOU specifically do? Use 'I' not 'we'", prompt: "The specific actions I took were: " },
      { icon: "R", label: "Result", tip: "Quantify the outcome — metrics, impact, lessons", prompt: "The result was: " },
    ],
  },
  system_design: {
    title: "Design Framework",
    tools: [
      { icon: "R", label: "Requirements", tip: "Clarify functional & non-functional requirements", prompt: "Let me clarify the requirements: " },
      { icon: "E", label: "Estimation", tip: "Back-of-envelope: QPS, storage, bandwidth", prompt: "Here are my capacity estimates: " },
      { icon: "A", label: "Architecture", tip: "High-level components, APIs, data flow", prompt: "For the high-level architecture, I would use: " },
      { icon: "T", label: "Tradeoffs", tip: "Discuss alternatives and why you chose this approach", prompt: "The key tradeoffs to consider are: " },
    ],
  },
  coding_discussion: {
    title: "Coding Framework",
    tools: [
      { icon: "O", label: "Complexity", tip: "Analyze time & space complexity (Big-O)", prompt: "The time complexity is O() and space complexity is O() because: " },
      { icon: "E", label: "Edge Cases", tip: "Empty input, overflow, concurrent access", prompt: "The edge cases to handle are: " },
      { icon: "T", label: "Testing", tip: "Unit tests, integration tests, property-based", prompt: "For testing, I would write: " },
      { icon: "R", label: "Review", tip: "Code review: readability, naming, SOLID", prompt: "From a code review perspective: " },
    ],
  },
  negotiation: {
    title: "Negotiation Framework",
    tools: [
      { icon: "A", label: "Anchor", tip: "Set a strong initial number with justification", prompt: "Based on my research, I'd like to propose a base salary of: " },
      { icon: "C", label: "Counter", tip: "Respond to offers — never accept the first one", prompt: "I appreciate the offer. Based on market data, I'd like to counter with: " },
      { icon: "V", label: "Value", tip: "Articulate your unique value and market data", prompt: "The unique value I bring includes: " },
      { icon: "P", label: "Package", tip: "Consider total comp: base, equity, benefits, signing", prompt: "Looking at the total compensation package, I'd like to discuss: " },
    ],
  },
};

// ── AI Avatar ───────────────────────────────────────────────────────────────

function AIAvatar({ speaking, processing, size = "lg" }: { speaking: boolean; processing: boolean; size?: "sm" | "lg" }) {
  const dim = size === "lg" ? "w-28 h-28" : "w-16 h-16";
  const iconSize = size === "lg" ? 40 : 24;
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className={`relative ${dim} rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg transition-all duration-300 ${
        speaking ? "shadow-indigo-300/50 scale-105" : processing ? "shadow-violet-300/30" : "shadow-slate-200"
      }`}>
        {speaking && (
          <>
            <div className="absolute inset-0 rounded-full bg-indigo-400/30 animate-ping" />
            <div className="absolute -inset-1 rounded-full bg-indigo-400/20 animate-pulse" />
          </>
        )}
        {processing && (
          <div className="absolute -inset-1 rounded-full border-2 border-violet-300 border-t-transparent animate-spin" />
        )}
        <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a4 4 0 0 1 4 4v4a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z" fill="white" fillOpacity="0.2" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
          <line x1="8" y1="22" x2="16" y2="22" />
        </svg>
      </div>
      <span className="text-xs text-slate-400 font-medium">
        {speaking ? "Speaking..." : processing ? "Thinking..." : "AI Interviewer"}
      </span>
    </div>
  );
}

// ── User Camera ─────────────────────────────────────────────────────────────

function UserCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [active, setActive] = useState(false);
  const [denied, setDenied] = useState<false | "denied" | "no-camera">(false);
  const streamRef = useRef<MediaStream | null>(null);

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: "user" },
      });
      streamRef.current = stream;
      setActive(true);
      setDenied(false);
    } catch (err) {
      // NotAllowedError = user blocked permission; NotFoundError = no camera
      const name = err instanceof Error ? err.name : "";
      setDenied(name === "NotFoundError" ? "no-camera" : "denied");
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setActive(false);
  }

  // Attach stream to video element after it mounts
  useEffect(() => {
    if (active && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [active]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  if (!active) {
    return (
      <div className="flex flex-col items-center gap-1.5">
        <button
          onClick={startCamera}
          className="w-32 h-32 rounded-full bg-slate-100 border-2 border-dashed border-slate-300 flex items-center justify-center hover:bg-slate-50 hover:border-indigo-300 transition-all group"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400 group-hover:text-indigo-500 transition-colors">
            <path d="M23 7l-7 5 7 5V7z" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
        </button>
        <span className="text-xs text-slate-400 text-center max-w-[130px] leading-tight">
          {denied === "denied"
            ? "Blocked — allow in browser settings"
            : denied === "no-camera"
            ? "No camera found"
            : "Enable camera (optional)"}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-32 h-32 rounded-full overflow-hidden border-2 border-indigo-200 shadow-sm">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-full object-cover scale-x-[-1]"
        />
        <button
          onClick={stopCamera}
          className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600 shadow-sm"
          aria-label="Stop camera"
        >
          x
        </button>
      </div>
      <span className="text-xs text-slate-400">You</span>
    </div>
  );
}

// ── Waveform ────────────────────────────────────────────────────────────────

function Waveform({ data, active }: { data: Uint8Array | null; active: boolean }) {
  const bars = 24;
  return (
    <div className="flex items-center gap-[2px] h-8">
      {Array.from({ length: bars }).map((_, i) => {
        const val = data ? (data[Math.floor((i / bars) * data.length)] ?? 0) : 0;
        const pct = active && data ? Math.max(8, (val / 255) * 100) : 8;
        return (
          <div
            key={i}
            className="w-[2px] rounded-full transition-all duration-75"
            style={{
              height: `${pct}%`,
              backgroundColor: active ? `hsl(${220 + (val / 255) * 60} 70% 60%)` : "#e2e8f0",
            }}
          />
        );
      })}
    </div>
  );
}

// ── State badge ─────────────────────────────────────────────────────────────

const STATE_META: Record<SessionState, { label: string; color: string }> = {
  idle:         { label: "Ready",         color: "bg-slate-100 text-slate-500" },
  connecting:   { label: "Connecting...", color: "bg-amber-50 text-amber-600" },
  reconnecting: { label: "Reconnecting", color: "bg-orange-50 text-orange-600" },
  listening:    { label: "Listening",     color: "bg-green-50 text-green-600" },
  processing:   { label: "Thinking...",   color: "bg-violet-50 text-violet-600" },
  speaking:     { label: "Speaking",      color: "bg-indigo-50 text-indigo-600" },
  error:        { label: "Error",         color: "bg-red-50 text-red-600" },
};

// ── Transcript bubble ───────────────────────────────────────────────────────

function TurnBubble({ entry }: { entry: TranscriptEntry }) {
  const isUser = entry.role === "user";
  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold mt-0.5 ${
        isUser ? "bg-indigo-100 text-indigo-600" : "bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
      }`}>
        {isUser ? "Y" : "AI"}
      </div>
      <div
        className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-900 dark:text-indigo-200 rounded-2xl rounded-tr-md"
            : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-2xl rounded-tl-md shadow-sm"
        } ${!entry.isFinal && entry.role === "assistant" ? "opacity-50 italic" : ""}`}
      >
        {entry.text}
      </div>
    </div>
  );
}

// ── Tools sidebar ───────────────────────────────────────────────────────────

function FrameworkPanel({ sessionType, onToolClick }: { sessionType: string; onToolClick: (prompt: string) => void }) {
  const config = INTERVIEW_TOOLS[sessionType];
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  if (!config) return null;

  return (
    <div className="p-3 space-y-1.5 overflow-y-auto">
      <p className="text-[10px] text-slate-400 mb-2">Click a step to insert into chat</p>
      {config.tools.map((tool, idx) => (
        <button
          key={tool.label}
          onClick={() => { onToolClick(tool.prompt); setActiveIdx(idx); }}
          className={`w-full text-left transition-all rounded-xl p-2.5 border ${
            activeIdx === idx
              ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-900/30 dark:border-indigo-700"
              : "hover:bg-slate-50 dark:hover:bg-slate-800 border-transparent"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <span className={`w-7 h-7 rounded-lg text-white text-xs font-bold flex items-center justify-center shrink-0 ${
              activeIdx === idx ? "bg-gradient-to-br from-indigo-600 to-violet-700" : "bg-gradient-to-br from-indigo-400 to-violet-500"
            }`}>
              {tool.icon}
            </span>
            <span className={`text-sm font-medium ${activeIdx === idx ? "text-indigo-700 dark:text-indigo-300" : "text-slate-700 dark:text-slate-300"}`}>
              {tool.label}
            </span>
          </div>
          <p className="text-xs text-slate-400 pl-[2.375rem] mt-0.5 leading-relaxed">{tool.tip}</p>
        </button>
      ))}
    </div>
  );
}

function ToolsSidebar({
  sessionType,
  onToolClick,
  onBoardChange,
  onCodeChange,
}: {
  sessionType: string;
  onToolClick: (prompt: string) => void;
  onBoardChange?: (items: DrawItem[]) => void;
  onCodeChange?: (code: string, lang: string, output?: string) => void;
}) {
  const hasCanvas   = sessionType === "system_design";
  const hasNotebook = sessionType === "coding_discussion";
  const hasFramework = !!INTERVIEW_TOOLS[sessionType];

  type Tab = "canvas" | "code" | "framework";
  const defaultTab: Tab = hasCanvas ? "canvas" : hasNotebook ? "code" : "framework";
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab);

  if (!hasCanvas && !hasNotebook && !hasFramework) return null;

  const tabs: { id: Tab; label: string }[] = [];
  if (hasCanvas)    tabs.push({ id: "canvas",    label: "Canvas" });
  if (hasNotebook)  tabs.push({ id: "code",      label: "Code" });
  if (hasFramework) tabs.push({ id: "framework", label: INTERVIEW_TOOLS[sessionType]?.title ?? "Framework" });

  return (
    <div className="flex flex-col w-full h-full bg-white/80 dark:bg-slate-900/90 backdrop-blur-md overflow-hidden">
      {/* Tab bar */}
      {tabs.length > 1 && (
        <div className="shrink-0 flex border-b border-slate-200/60 dark:border-slate-700/60">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-indigo-600 border-b-2 border-indigo-500 dark:text-indigo-400"
                  : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {activeTab === "canvas" && <DrawingCanvas onItemsChange={onBoardChange} />}
        {activeTab === "code" && (
          <CodeNotebook
            onSendToChat={(code, lang) => onToolClick(`Here is my ${lang} solution:\n\`\`\`${lang}\n${code}\n\`\`\``)}
            onCodeChange={onCodeChange}
          />
        )}
        {activeTab === "framework" && (
          <FrameworkPanel sessionType={sessionType} onToolClick={onToolClick} />
        )}
      </div>
    </div>
  );
}

// ── Text input ──────────────────────────────────────────────────────────────

function TextInput({ onSend, disabled, prefill, prefillSeq }: { onSend: (text: string) => void; disabled?: boolean; prefill?: string; prefillSeq?: number }) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // When a tool inserts a prefill, update the input and focus it
  useEffect(() => {
    if (prefill) {
      setValue(prefill);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [prefill, prefillSeq]);

  const submit = () => {
    const t = value.trim();
    if (!t) return;
    onSend(t);
    setValue("");
  };
  return (
    <div className="flex gap-2">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="Type your answer..."
        disabled={disabled}
        className="flex-1 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={disabled}
        className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl text-sm font-medium hover:from-indigo-700 hover:to-violet-700 shadow-sm disabled:opacity-50"
      >
        Send
      </button>
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function SessionPage() {
  const { ready } = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const accessToken =
    typeof window !== "undefined" ? (localStorage.getItem("access_token") ?? "") : "";

  // Convert http(s):// API URL to ws(s):// for WebSocket — keeps WS consistent with REST base
  const wsBase = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080")
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:");

  const { state, transcript, latency, waveformData, textMode, connect, disconnect, sendText, updateToolContext, error, softPrompt } =
    useVoiceSession({ sessionId: id, accessToken, apiBaseUrl: wsBase });

  const [sessionInfo, setSessionInfo] = useState<SessionResponse | null>(null);
  const [toolPrefill, setToolPrefill] = useState<{ text: string; seq: number } | undefined>(undefined);
  const [elapsed, setElapsed] = useState(0);
  const [showSummary, setShowSummary] = useState(false);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const finalElapsed = useRef(0);
  // 0 = hidden, 1–99 = split (% of total width), 100 = full-screen panel
  const [panelWidth, setPanelWidth] = useState(0);
  const isDraggingDivider = useRef(false);
  const contentAreaRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch session info to get the type
  useEffect(() => {
    if (!ready) return;
    api.sessions.get(id)
      .then((s) => {
        setSessionInfo(s);
        if (["system_design", "coding_discussion"].includes(s.type)) {
          setPanelWidth(50);
        } else if (INTERVIEW_TOOLS[s.type]) {
          setPanelWidth(33);
        }
      })
      .catch(() => { /* will show generic UI */ });
  }, [id, ready]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [transcript]);

  // Elapsed timer — starts when session becomes active
  const sessionActive = !["idle", "error"].includes(state);
  useEffect(() => {
    if (!sessionActive) { setElapsed(0); return; }
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [sessionActive]);

  const isActive = !["idle", "error"].includes(state);
  const stateInfo = STATE_META[state];
  const sessionType = sessionInfo?.type ?? "behavioral";
  const hasSplitPanel = !!INTERVIEW_TOOLS[sessionType];
  const questionCount = transcript.filter((e) => e.role === "assistant").length;
  const elapsedStr = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  // ── Tool context callbacks — keep AI interviewer aware of board/code ──────
  const isSessionActive = state !== "idle" && state !== "error";

  const handleBoardChange = useCallback(
    (items: DrawItem[]) => {
      if (!isSessionActive) return;
      updateToolContext(describeBoardItems(items));
    },
    [isSessionActive, updateToolContext],
  );

  const handleCodeChange = useCallback(
    (code: string, lang: string, output?: string) => {
      if (!isSessionActive) return;
      const desc = describeCode(code, lang, output);
      updateToolContext(desc || null);
    },
    [isSessionActive, updateToolContext],
  );

  async function handleEnd() {
    finalElapsed.current = elapsed; // capture before disconnect resets state
    disconnect();
    try {
      await api.sessions.end(id);
    } catch {
      /* already ended */
    }
    setShowSummary(true);
    setTimeout(() => router.push(`/sessions/${id}/transcript`), 3500);
  }

  function handleBack() {
    if (isActive) {
      handleEnd();
    } else {
      router.push("/sessions");
    }
  }

  // Friendly error message for pipeline connection issues
  const friendlyError = error?.includes("pipeline")
    ? "Voice pipeline unavailable — the AI voice service requires active API connections (Deepgram, Claude, ElevenLabs). You can use text mode below or check your API keys."
    : error;

  return (
    <main className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-900">
      {/* Session-over summary overlay — B1 */}
      {showSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-800 rounded-3xl p-10 shadow-2xl max-w-sm w-full mx-4 text-center space-y-5">
            <div className="w-16 h-16 bg-indigo-50 dark:bg-indigo-950/50 rounded-2xl flex items-center justify-center mx-auto">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="1.75" strokeLinecap="round"><path d="M20 6L9 17l-5-5"/></svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Session complete</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Loading your results…</p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-left">
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide font-medium">Questions</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-0.5">{questionCount}</p>
              </div>
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3">
                <p className="text-xs text-slate-400 uppercase tracking-wide font-medium">Duration</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                  {Math.floor(finalElapsed.current / 60)}:{String(finalElapsed.current % 60).padStart(2, "0")}
                </p>
              </div>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1 overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full animate-[progress_3.5s_linear_forwards]" style={{ width: "100%", transformOrigin: "left" }} />
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <header className="bg-white/80 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-700/60 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={handleBack} className="text-slate-400 hover:text-slate-700 transition-colors" aria-label="Back">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 4l-6 6 6 6" />
            </svg>
          </button>
          <span className="text-sm font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">InterviewCraft</span>
          <span className="text-slate-300">|</span>
          <span className="text-xs text-slate-500 font-medium">{sessionType.replace(/_/g, " ")}</span>
          {isActive && questionCount > 0 && (
            <span className="text-xs font-mono text-slate-400">Q{questionCount}</span>
          )}
          {isActive && (
            <span className="text-xs font-mono text-slate-400">{elapsedStr}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${stateInfo.color}`}>
            {stateInfo.label}
          </span>
          {latency.e2eMs && (
            <span className={`hidden md:inline text-xs font-mono px-2 py-1 rounded-full ${
              latency.e2eMs < 800 ? "bg-green-50 text-green-600" : latency.e2eMs < 1000 ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"
            }`}>
              {latency.e2eMs}ms
            </span>
          )}
          {hasSplitPanel && (
            <div className="flex items-center gap-0.5 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
              {([
                { w: 0,   label: "✕",   title: "Hide panel" },
                { w: 33,  label: "⅓",   title: "1/3 panel" },
                { w: 50,  label: "½",   title: "Half & half" },
                { w: 67,  label: "⅔",   title: "2/3 panel" },
                { w: 100, label: "⛶",  title: "Full screen" },
              ] as const).map(({ w, label, title }) => (
                <button
                  key={w}
                  onClick={() => setPanelWidth(w)}
                  title={title}
                  className={`px-2 py-1.5 text-xs font-medium transition-colors ${
                    panelWidth === w
                      ? "bg-indigo-600 text-white"
                      : "text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Main content area — participants + transcript + tools */}
      <div ref={contentAreaRef} className="flex-1 flex min-h-0">
        {/* Center column — avatars, transcript, controls */}
        <div
          className="flex flex-col min-h-0 overflow-hidden"
          style={{ width: panelWidth === 100 ? "0" : panelWidth > 0 ? `${100 - panelWidth}%` : "100%", display: panelWidth === 100 ? "none" : undefined }}
        >
          {/* Participants bar — AI avatar + camera */}
          <div className="flex items-center justify-center gap-8 py-4 px-4 border-b border-slate-100 dark:border-slate-700/60 bg-white/40 dark:bg-slate-800/60">
            <AIAvatar
              speaking={state === "speaking"}
              processing={state === "processing"}
              size={isActive ? "lg" : "sm"}
            />
            <div className="w-px h-12 bg-slate-200" />
            <UserCamera />
          </div>

          {/* Transcript */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">
            {transcript.length === 0 && !isActive && !friendlyError && (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm gap-2 pt-8">
                <p className="font-medium text-slate-500">Ready to practice</p>
                <p className="text-xs">Press Start to begin your voice session, or type below</p>
              </div>
            )}
            {transcript.map((entry, i) => <TurnBubble key={i} entry={entry} />)}
            {/* Recording indicator — mic icon + audio-reactive bars */}
            {state === "listening" && isActive && (
              <div className="flex gap-2.5">
                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 text-xs font-bold mt-0.5">Y</div>
                <div className="bg-indigo-50 rounded-2xl rounded-tr-md px-4 py-3 flex items-center gap-2">
                  <svg className="w-4 h-4 text-emerald-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 01-14 0v-2M12 19v3M8 22h8" />
                  </svg>
                  <div className="flex gap-0.5 items-end h-4">
                    {Array.from({ length: 4 }).map((_, i) => {
                      const raw = waveformData ? (waveformData[Math.floor((i / 4) * waveformData.length)] ?? 0) : 0;
                      const pct = Math.max(20, (raw / 255) * 100);
                      return (
                        <div
                          key={i}
                          className="w-1 bg-emerald-400 rounded-full transition-all duration-75"
                          style={{ height: `${pct}%` }}
                        />
                      );
                    })}
                  </div>
                  <span className="text-xs text-slate-500">Listening...</span>
                </div>
              </div>
            )}
            {/* Soft-prompt toast — floats above transcript, auto-dismisses */}
            {softPrompt && (
              <div className="sticky bottom-0 flex justify-center pointer-events-none">
                <span className="px-4 py-2 bg-slate-700/80 text-slate-200 text-xs rounded-full backdrop-blur-sm shadow-lg">
                  {softPrompt}
                </span>
              </div>
            )}
          </div>

          {/* Error banner */}
          {friendlyError && (
            <div className="mx-4 mb-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 leading-relaxed flex items-start gap-3">
              <span className="shrink-0 mt-0.5">&#9888;</span>
              <div className="flex-1">
                <p>{friendlyError}</p>
                {state === "error" && (
                  <button
                    onClick={connect}
                    className="mt-2 px-4 py-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    Retry Connection
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Text mode banner */}
          {textMode && isActive && (
            <div className="mx-4 mb-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
              Switched to text mode — microphone signal too low.
            </div>
          )}

          {/* Controls */}
          <footer className="bg-white/80 dark:bg-slate-900/90 backdrop-blur-md border-t border-slate-200/60 dark:border-slate-700/60 px-4 py-3 shrink-0 space-y-2.5">
            {/* Text input — always visible */}
            <TextInput
              onSend={sendText}
              disabled={!isActive && state !== "idle"}
              prefill={toolPrefill?.text}
              prefillSeq={toolPrefill?.seq}
            />

            <div className="flex items-center gap-3">
              <div className="flex-1">
                <Waveform data={waveformData} active={state === "listening"} />
              </div>

              {isActive ? (
                <button
                  onClick={handleEnd}
                  className="px-5 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl text-sm font-medium transition-colors shadow-sm"
                >
                  End Session
                </button>
              ) : (
                <button
                  onClick={() => setShowConsentModal(true)}
                  className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-xl text-sm font-medium transition-all shadow-sm shadow-indigo-200"
                >
                  Start Session
                </button>
              )}
            </div>
          </footer>
        </div>

        {/* Drag handle — only when split (not hidden, not full) */}
        {hasSplitPanel && panelWidth > 0 && panelWidth < 100 && (
          <div
            className="w-1.5 shrink-0 bg-slate-200/80 dark:bg-slate-700/60 hover:bg-indigo-400 dark:hover:bg-indigo-500 cursor-col-resize transition-colors select-none"
            title="Drag to resize"
            onPointerDown={(e) => {
              isDraggingDivider.current = true;
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerMove={(e) => {
              if (!isDraggingDivider.current) return;
              const container = contentAreaRef.current;
              if (!container) return;
              const rect = container.getBoundingClientRect();
              const pct = ((rect.right - e.clientX) / rect.width) * 100;
              setPanelWidth(Math.max(15, Math.min(90, Math.round(pct))));
            }}
            onPointerUp={() => { isDraggingDivider.current = false; }}
            onPointerCancel={() => { isDraggingDivider.current = false; }}
          />
        )}

        {/* Right panel */}
        {hasSplitPanel ? (
          panelWidth > 0 && (
            <div
              className="flex flex-col border-l border-slate-200/60 dark:border-slate-700/60 overflow-hidden"
              style={{ width: panelWidth === 100 ? "100%" : `${panelWidth}%` }}
            >
              <ToolsSidebar sessionType={sessionType} onToolClick={(prompt) => setToolPrefill({ text: prompt, seq: Date.now() })} onBoardChange={handleBoardChange} onCodeChange={handleCodeChange} />
            </div>
          )
        ) : (
          <ToolsSidebar sessionType={sessionType} onToolClick={(prompt) => setToolPrefill({ text: prompt, seq: Date.now() })} onBoardChange={handleBoardChange} onCodeChange={handleCodeChange} />
        )}
      </div>

      {/* Recording Consent Modal (P0-C) */}
      {showConsentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-2xl max-w-md w-full mx-4 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-indigo-50 dark:bg-indigo-950/50 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Microphone & Recording Consent</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  This session uses your microphone for real-time speech recognition.
                </p>
              </div>
            </div>
            <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                Audio is processed in real-time by Deepgram and <strong>never stored</strong> on our servers.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                Only the text transcript of your answers is saved.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                You can delete all your data anytime in Settings → Delete Account.
              </li>
            </ul>
            <p className="text-xs text-slate-400">
              By starting this session you consent to real-time transcription. See our{" "}
              <a href="/privacy" target="_blank" className="text-indigo-500 hover:underline">Privacy Policy</a> for details.
            </p>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => { setShowConsentModal(false); connect(); }}
                className="flex-1 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-xl text-sm font-semibold transition-all"
              >
                I understand — Start Session
              </button>
              <button
                onClick={() => setShowConsentModal(false)}
                className="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-xl transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
