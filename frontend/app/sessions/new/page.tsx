"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError, JdAnalysisResponse, CompanyIntelItem, CompanyIntelListResponse } from "@/lib/api";
import { AppNav } from "@/components/AppNav";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

type SessionType = "behavioral" | "system_design" | "coding_discussion" | "negotiation" | "debrief";

const DURATION_DEFAULTS: Record<SessionType, number> = {
  behavioral: 35,
  system_design: 50,
  coding_discussion: 35,
  negotiation: 20,
  debrief: 25,
};
type QualityProfile = "quality" | "balanced" | "budget";
type Persona = "neutral" | "friendly" | "tough";
type Company = "google" | "meta" | "amazon" | "microsoft" | "apple" | "netflix" | "uber" | "stripe" | "linkedin" | "airbnb" | "nvidia" | "spotify" | null;

const SESSION_TYPES = [
  { value: "behavioral", label: "Behavioral", desc: "STAR stories, leadership, conflict" },
  { value: "system_design", label: "System Design", desc: "Architecture, scale, tradeoffs" },
  { value: "coding_discussion", label: "Coding Discussion", desc: "Complexity, edge cases, testing" },
  { value: "negotiation", label: "Salary Negotiation", desc: "Anchor, counter, equity" },
  { value: "debrief", label: "Post-Interview Debrief", desc: "Reflect on a real interview with a coach" },
] as const;

const QUALITY_PROFILES: { value: QualityProfile; label: string; cost: string; detail: string }[] = [
  { value: "quality", label: "Quality", cost: "$0.60-1.30", detail: "Sonnet + ElevenLabs" },
  { value: "balanced", label: "Balanced", cost: "$0.30-0.60", detail: "Sonnet voice, Haiku scoring" },
  { value: "budget", label: "Budget", cost: "$0.15-0.30", detail: "Haiku + Deepgram TTS" },
];

const PERSONAS: { value: Persona; label: string; icon: string; desc: string; color: string }[] = [
  {
    value: "friendly",
    label: "Friendly",
    icon: "😊",
    desc: "Warm, encouraging, hints available",
    color: "border-emerald-400 bg-emerald-50 ring-emerald-400/20 text-emerald-700",
  },
  {
    value: "neutral",
    label: "Neutral",
    icon: "🎯",
    desc: "Balanced, professional (default)",
    color: "border-indigo-500 bg-indigo-50 ring-indigo-500/20 text-indigo-700",
  },
  {
    value: "tough",
    label: "Tough",
    icon: "🔥",
    desc: "Skeptical, challenging, L6 bar",
    color: "border-orange-400 bg-orange-50 ring-orange-400/20 text-orange-700",
  },
];

const COMPANIES: { value: Company; label: string; abbr: string; color: string }[] = [
  { value: null, label: "Generic", abbr: "—", color: "border-slate-200 text-slate-500" },
  { value: "google", label: "Google", abbr: "G", color: "border-blue-400 text-blue-600 bg-blue-50" },
  { value: "meta", label: "Meta", abbr: "M", color: "border-indigo-500 text-indigo-700 bg-indigo-50" },
  { value: "amazon", label: "Amazon", abbr: "A", color: "border-orange-400 text-orange-700 bg-orange-50" },
  { value: "microsoft", label: "Microsoft", abbr: "MS", color: "border-teal-500 text-teal-700 bg-teal-50" },
  { value: "apple", label: "Apple", abbr: "", color: "border-slate-700 text-slate-900 bg-slate-100" },
  { value: "netflix", label: "Netflix", abbr: "N", color: "border-red-500 text-red-700 bg-red-50" },
  { value: "uber", label: "Uber", abbr: "U", color: "border-gray-900 text-gray-900 bg-gray-100" },
  { value: "stripe", label: "Stripe", abbr: "S", color: "border-violet-500 text-violet-700 bg-violet-50" },
  { value: "linkedin", label: "LinkedIn", abbr: "in", color: "border-sky-600 text-sky-700 bg-sky-50" },
  { value: "airbnb", label: "Airbnb", abbr: "Air", color: "border-rose-400 text-rose-700 bg-rose-50" },
  { value: "nvidia", label: "Nvidia", abbr: "NV", color: "border-green-500 text-green-700 bg-green-50" },
  { value: "spotify", label: "Spotify", abbr: "SP", color: "border-emerald-500 text-emerald-700 bg-emerald-50" },
];

const ELEVENLABS_VOICES = [
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel", desc: "Female, calm, neutral" },
  { id: "TxGEqnHWrfWFTfGW9XjX", name: "Josh", desc: "Male, deep, confident" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella", desc: "Female, soft, warm" },
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam", desc: "Male, professional" },
  { id: "ErXwobaYiN019PkySvjV", name: "Antoni", desc: "Male, clear, engaging" },
  { id: "jBpfuIE2acCO8z3wKNLl", name: "Emily", desc: "Female, bright, friendly" },
  { id: "AZnzlk1XvdvUeBnXmlld", name: "Domi", desc: "Female, strong, expressive" },
  { id: "yoZ06aMxZJJ28mfd3POQ", name: "Sam", desc: "Male, raspy, authentic" },
];

const DEEPGRAM_VOICES = [
  { id: "aura-asteria-en", name: "Asteria", desc: "Female, smooth, neutral" },
  { id: "aura-luna-en", name: "Luna", desc: "Female, soft, warm" },
  { id: "aura-stella-en", name: "Stella", desc: "Female, clear, bright" },
  { id: "aura-hera-en", name: "Hera", desc: "Female, confident, rich" },
  { id: "aura-orion-en", name: "Orion", desc: "Male, deep, authoritative" },
  { id: "aura-arcas-en", name: "Arcas", desc: "Male, clear, professional" },
];

function FreeSessionBanner({
  sessionCount,
  hasAnthropicKey,
}: {
  sessionCount: number | null;
  hasAnthropicKey: boolean | null;
}) {
  // Still loading -- show nothing to avoid flicker
  if (sessionCount === null || hasAnthropicKey === null) return null;
  // User has their own key -- no need to show anything
  if (hasAnthropicKey) return null;

  if (sessionCount === 0) {
    return (
      <div className="mb-5 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300">
        <span className="font-medium">1 free session included.</span>{" "}
        After that, add your own key in{" "}
        <Link href="/settings" className="underline underline-offset-2 hover:text-indigo-900 dark:hover:text-indigo-100">
          Settings
        </Link>{" "}
        to continue. STT and TTS remain covered by the platform.
      </div>
    );
  }

  return (
    <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
      <span className="font-medium">Free session used.</span>{" "}
      Add your LLM key in{" "}
      <Link href="/settings" className="underline underline-offset-2 hover:text-amber-900 dark:hover:text-amber-100">
        Settings
      </Link>{" "}
      to start more sessions. STT and TTS remain covered by the platform.
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-white inline-block mr-2"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function NewSessionForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const focusSkill = searchParams.get("skill");

  const [sessionType, setSessionType] = useState<SessionType>("behavioral");
  const [profile, setProfile] = useState<QualityProfile>("balanced");
  const [voiceId, setVoiceId] = useState(ELEVENLABS_VOICES[0].id);
  const [persona, setPersona] = useState<Persona>("neutral");
  const [company, setCompany] = useState<Company>(null);
  const [durationMinutes, setDurationMinutes] = useState(DURATION_DEFAULTS.behavioral);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // JD Analyzer state
  const [jdText, setJdText] = useState("");
  const [jdOpen, setJdOpen] = useState(false);
  const [jdLoading, setJdLoading] = useState(false);
  const [jdResult, setJdResult] = useState<JdAnalysisResponse | null>(null);
  const [jdError, setJdError] = useState<string | null>(null);

  // Company Intel state
  const [intelData, setIntelData] = useState<CompanyIntelListResponse | null>(null);
  const [intelOpen, setIntelOpen] = useState(false);
  const [intelLoading, setIntelLoading] = useState(false);
  const [intelSubmitText, setIntelSubmitText] = useState("");
  const [intelSubmitCategory, setIntelSubmitCategory] = useState("process");
  const [intelSubmitting, setIntelSubmitting] = useState(false);

  // Free-session gating state
  const [sessionCount, setSessionCount] = useState<number | null>(null);
  const [hasAnthropicKey, setHasAnthropicKey] = useState<boolean | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }
    // Fetch current session count + BYOK state to drive the free-session banner.
    // Both calls are independent and degrade gracefully on error.
    api.sessions
      .list(100)
      .then((list) => setSessionCount(list.length))
      .catch(() => setSessionCount(null));
    api.settings
      .get()
      .then((s) => setHasAnthropicKey(s.byok_providers.includes("anthropic")))
      .catch(() => setHasAnthropicKey(null));
  }, [router]);

  // Reset voice to appropriate default when switching between budget and non-budget profiles
  useEffect(() => {
    if (profile === "budget") {
      setVoiceId(DEEPGRAM_VOICES[0].id);
    } else {
      setVoiceId(ELEVENLABS_VOICES[0].id);
    }
  }, [profile]);

  // Reset duration to type default when session type changes
  useEffect(() => {
    setDurationMinutes(DURATION_DEFAULTS[sessionType]);
  }, [sessionType]);

  // Load company intel when a company is selected and the panel is opened
  useEffect(() => {
    if (!company || !intelOpen) return;
    setIntelLoading(true);
    api.companies.getIntel(company)
      .then(setIntelData)
      .catch(() => setIntelData(null))
      .finally(() => setIntelLoading(false));
  }, [company, intelOpen]);

  async function submitIntel() {
    if (!company || !intelSubmitText.trim()) return;
    setIntelSubmitting(true);
    try {
      const item = await api.companies.submitIntel(company, intelSubmitCategory, intelSubmitText.trim());
      setIntelData((prev) => prev
        ? { ...prev, items: [item, ...prev.items], total: prev.total + 1 }
        : { company, items: [item], total: 1 }
      );
      setIntelSubmitText("");
    } catch { /* silent */ }
    finally { setIntelSubmitting(false); }
  }

  async function upvoteIntel(item: CompanyIntelItem) {
    if (!company) return;
    try {
      const res = await api.companies.upvote(company, item.id);
      setIntelData((prev) => prev
        ? { ...prev, items: prev.items.map((i) => i.id === item.id ? { ...i, upvotes: res.upvotes } : i) }
        : prev
      );
    } catch { /* silent */ }
  }

  async function startSession() {
    setLoading(true);
    setError(null);
    try {
      const session = await api.sessions.create(sessionType, profile, undefined, voiceId, persona, company, focusSkill ?? undefined, durationMinutes);
      router.push(`/sessions/${session.id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message.includes("credentials") || err.message.includes("401")) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }
        if (err instanceof ApiError && err.status === 402) {
          router.push("/settings?byok=anthropic");
          return;
        }
        setError(err.message);
      } else {
        setError("Failed to start session");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeJd() {
    if (jdText.trim().length < 50) {
      setJdError("Paste at least 50 characters of the job description.");
      return;
    }
    setJdLoading(true);
    setJdError(null);
    setJdResult(null);
    try {
      const result = await api.sessions.analyzeJd(jdText);
      setJdResult(result);
      // Auto-apply suggested values
      if (result.suggested_session_type) {
        setSessionType(result.suggested_session_type as SessionType);
      }
      if (result.suggested_company) {
        setCompany(result.suggested_company as Company);
      }
    } catch (e) {
      setJdError(e instanceof ApiError ? e.message : "Analysis failed. Please try again.");
    } finally {
      setJdLoading(false);
    }
  }

  const PRIORITY_COLOR: Record<string, string> = {
    high: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/30 dark:text-red-300 dark:border-red-800",
    medium: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-800",
    low: "bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-900">
      <AppNav showBack />
      <div className="flex items-start justify-center p-4 sm:p-6 lg:p-8 min-h-[calc(100vh-3.5rem)]">
        <div className="card w-full max-w-lg xl:max-w-2xl p-5 sm:p-8 animate-fade-in">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">New Session</h1>
          {focusSkill ? (
            <div className="flex items-center gap-2 mb-4 mt-1">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 rounded-full text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
                Targeting: {focusSkill.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              </span>
              <span className="text-xs text-slate-400">Questions will focus on this skill</span>
            </div>
          ) : (
            <p className="text-slate-500 text-sm mb-5">
              Choose your interview type and quality profile.
            </p>
          )}

          <FreeSessionBanner sessionCount={sessionCount} hasAnthropicKey={hasAnthropicKey} />

          {/* JD Analyzer */}
          <section className="mb-5">
            <button
              type="button"
              onClick={() => setJdOpen((o) => !o)}
              className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg border border-dashed border-indigo-300 dark:border-indigo-700 bg-indigo-50/50 dark:bg-indigo-950/20 text-sm text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors"
            >
              <span className="font-medium flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                Paste Job Description
              </span>
              <span className="text-xs text-indigo-400">{jdOpen ? "▲ hide" : "▼ auto-configure"}</span>
            </button>

            {jdOpen && (
              <div className="mt-2 space-y-2">
                <textarea
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="Paste the full job description here..."
                  rows={6}
                  className="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-2.5 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400/50"
                />
                {jdError && (
                  <p className="text-xs text-red-500">{jdError}</p>
                )}
                <button
                  type="button"
                  onClick={handleAnalyzeJd}
                  disabled={jdLoading || jdText.trim().length < 50}
                  className="w-full py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 transition-colors"
                >
                  {jdLoading ? "Analyzing..." : "Analyze JD"}
                </button>

                {jdResult && (
                  <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/60 dark:bg-indigo-950/30 p-3 space-y-3 text-sm">
                    {/* Header row */}
                    <div className="flex flex-wrap gap-2 items-center">
                      <span className="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 rounded-full text-xs font-semibold capitalize">
                        {jdResult.seniority}
                      </span>
                      <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full text-xs capitalize">
                        {jdResult.role_type}
                      </span>
                      {jdResult.suggested_company && (
                        <span className="px-2 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 rounded-full text-xs font-semibold capitalize">
                          {jdResult.suggested_company}
                        </span>
                      )}
                      <span className="ml-auto text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                        ✓ Applied to session
                      </span>
                    </div>

                    {/* Required skills */}
                    {jdResult.skills_required.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">Required Skills</p>
                        <div className="flex flex-wrap gap-1">
                          {jdResult.skills_required.map((s) => (
                            <span key={s} className="px-2 py-0.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Nice to have */}
                    {jdResult.skills_nice_to_have.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Nice to Have</p>
                        <div className="flex flex-wrap gap-1">
                          {jdResult.skills_nice_to_have.map((s) => (
                            <span key={s} className="px-2 py-0.5 bg-white/60 dark:bg-slate-800/60 border border-dashed border-slate-200 dark:border-slate-600 rounded text-xs text-slate-500 dark:text-slate-400">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Focus areas */}
                    {jdResult.focus_areas.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5">Practice Focus</p>
                        <div className="space-y-1.5">
                          {jdResult.focus_areas.map((fa, i) => (
                            <div key={i} className={`flex items-start gap-2 px-2.5 py-1.5 rounded-lg border text-xs ${PRIORITY_COLOR[fa.priority]}`}>
                              <span className="font-semibold shrink-0 capitalize">{fa.priority}</span>
                              <span><strong>{fa.area}</strong> — {fa.reason}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Coaching note */}
                    {jdResult.coaching_note && (
                      <p className="text-xs text-indigo-700 dark:text-indigo-300 bg-indigo-100/60 dark:bg-indigo-900/40 rounded-lg px-3 py-2">
                        💡 {jdResult.coaching_note}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Session type */}
          <section className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-3">Interview Type</label>
            <div className="grid grid-cols-2 gap-2">
              {SESSION_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setSessionType(t.value)}
                  className={`text-left p-3 min-h-[60px] rounded-lg border transition-all interactive ${
                    sessionType === t.value
                      ? "border-indigo-500 bg-indigo-50 text-indigo-700 ring-2 ring-indigo-500/20"
                      : "border-slate-200 hover:border-slate-300 text-slate-700"
                  }`}
                >
                  <div className="font-medium text-xs sm:text-sm">{t.label}</div>
                  <div className="text-[10px] sm:text-xs text-slate-500 mt-0.5 leading-snug">{t.desc}</div>
                </button>
              ))}
            </div>
          </section>

          {/* Quality profile */}
          <section className="mb-8">
            <label className="block text-sm font-medium text-slate-700 mb-3">Quality Profile</label>
            <div className="space-y-2">
              {QUALITY_PROFILES.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setProfile(p.value)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                    profile === p.value
                      ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500/20"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <span>
                    <span className="font-medium text-sm text-slate-900">{p.label}</span>
                    <span className="text-xs text-slate-500 ml-2">{p.detail}</span>
                  </span>
                  <span className="text-[10px] sm:text-xs font-mono text-slate-500 shrink-0">{p.cost}/session</span>
                </button>
              ))}
            </div>
          </section>

          {/* Target Company */}
          <section className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-3">Target Company</label>
            <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-5 md:grid-cols-7">
              {COMPANIES.map((c) => (
                <button
                  key={String(c.value)}
                  onClick={() => setCompany(c.value)}
                  className={`flex flex-col items-center p-2 sm:p-2.5 min-h-[52px] rounded-lg border-2 transition-all text-center interactive ${
                    company === c.value
                      ? `${c.color} ring-2 ring-offset-1`
                      : "border-slate-200 hover:border-slate-300 text-slate-600"
                  }`}
                >
                  <span className="text-xs font-bold leading-none">{c.abbr}</span>
                  <span className="text-[10px] sm:text-xs mt-0.5 leading-tight">{c.label}</span>
                </button>
              ))}
            </div>
          </section>

          {/* Company Intel */}
          {company && (
            <section className="mb-6">
              <button
                onClick={() => setIntelOpen((v) => !v)}
                className="flex items-center justify-between w-full text-left text-sm font-medium text-slate-700 mb-2"
              >
                <span>
                  Community Intel — {COMPANIES.find((c) => c.value === company)?.label}
                  {intelData && intelData.total > 0 && (
                    <span className="ml-2 text-xs text-indigo-600 font-normal">{intelData.total} tip{intelData.total !== 1 ? "s" : ""}</span>
                  )}
                </span>
                <span className="text-slate-400 text-xs">{intelOpen ? "▲" : "▼"}</span>
              </button>

              {intelOpen && (
                <div className="space-y-3 border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-white dark:bg-slate-800">
                  {/* Existing intel */}
                  {intelLoading ? (
                    <p className="text-xs text-muted-foreground">Loading…</p>
                  ) : intelData && intelData.items.length > 0 ? (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {intelData.items.map((item) => (
                        <div key={item.id} className="flex gap-2 text-xs">
                          <span className="shrink-0 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 capitalize">
                            {item.category}
                          </span>
                          <span className="flex-1 text-slate-700 dark:text-slate-300">{item.content}</span>
                          <button
                            onClick={() => upvoteIntel(item)}
                            className="shrink-0 text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Upvote"
                          >
                            ▲ {item.upvotes}
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">No tips yet — be the first to share!</p>
                  )}

                  {/* Submit form */}
                  <div className="border-t border-slate-100 dark:border-slate-700 pt-3 space-y-2">
                    <div className="flex gap-2">
                      <select
                        value={intelSubmitCategory}
                        onChange={(e) => setIntelSubmitCategory(e.target.value)}
                        className="text-xs border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200"
                      >
                        <option value="process">Process</option>
                        <option value="technical">Technical</option>
                        <option value="culture">Culture</option>
                        <option value="tips">Tips</option>
                      </select>
                      <textarea
                        value={intelSubmitText}
                        onChange={(e) => setIntelSubmitText(e.target.value)}
                        placeholder="Share what you know about their interview process…"
                        rows={2}
                        maxLength={1000}
                        className="flex-1 text-xs border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <button
                      onClick={submitIntel}
                      disabled={intelSubmitting || intelSubmitText.trim().length < 20}
                      className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {intelSubmitting ? "Sharing…" : "Share Tip"}
                    </button>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Interviewer Persona */}
          <section className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-3">Interviewer Persona</label>
            <div className="grid grid-cols-3 gap-2">
              {PERSONAS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPersona(p.value)}
                  className={`text-left p-2.5 sm:p-3 min-h-[80px] rounded-lg border-2 transition-all ${
                    persona === p.value
                      ? `${p.color} ring-2`
                      : "border-slate-200 hover:border-slate-300 text-slate-700"
                  }`}
                >
                  <div className="text-base sm:text-lg mb-0.5">{p.icon}</div>
                  <div className="font-medium text-xs sm:text-sm">{p.label}</div>
                  <div className="text-[10px] sm:text-xs text-slate-500 mt-0.5 leading-snug">{p.desc}</div>
                </button>
              ))}
            </div>
          </section>

          {/* Bot voice */}
          <section className="mb-8">
            <Label htmlFor="voice-select" className="block text-sm font-medium text-slate-700 mb-1">
              Interviewer Voice
            </Label>
            <p className="text-xs text-slate-400 mb-2">
              {profile === "budget" ? "Deepgram Aura voices" : "ElevenLabs voices"}
            </p>
            <Select value={voiceId} onValueChange={(val) => setVoiceId(val as string)}>
              <SelectTrigger id="voice-select" className="w-full">
                <SelectValue placeholder="Select a voice" />
              </SelectTrigger>
              <SelectContent>
                {(profile === "budget" ? DEEPGRAM_VOICES : ELEVENLABS_VOICES).map((v) => (
                  <SelectItem key={v.id} value={v.id}>
                    {v.name} — {v.desc}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </section>

          {/* Duration */}
          <section className="mb-8">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Interview Duration
            </label>
            <p className="text-xs text-slate-400 mb-2">
              A countdown timer will run during the session — just like a real interview.
            </p>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={90}
                step={5}
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
                className="flex-1 accent-indigo-600"
              />
              <span className="text-sm font-mono font-semibold text-slate-700 dark:text-slate-300 w-14 text-right">
                {durationMinutes} min
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-400 mt-0.5 px-0.5">
              <span>5 min</span>
              <span>Default: {DURATION_DEFAULTS[sessionType]} min</span>
              <span>90 min</span>
            </div>
          </section>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <button
            onClick={startSession}
            disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-50 flex items-center justify-center"
          >
            {loading && <LoadingSpinner />}
            {loading ? "Starting..." : "Start Session"}
          </button>


        </div>
      </div>
    </main>
  );
}

// Force dynamic rendering to avoid SSR/client hydration mismatch from useSearchParams
export const dynamic = "force-dynamic";

export default function NewSessionPage() {
  return (
    <Suspense fallback={null}>
      <NewSessionForm />
    </Suspense>
  );
}
