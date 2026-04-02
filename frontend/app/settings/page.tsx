"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { api, SettingsResponse, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, CheckCircle2, XCircle, ExternalLink, Key } from "lucide-react";

const QUALITY_PROFILES = [
  {
    id: "quality",
    label: "Quality",
    description: "Sonnet for all tasks + ElevenLabs TTS",
    cost: "~$0.60–1.30/session",
    badge: "Best accuracy",
    badgeVariant: "default" as const,
  },
  {
    id: "balanced",
    label: "Balanced",
    description: "Sonnet voice, Haiku scoring/diff + ElevenLabs TTS",
    cost: "~$0.30–0.60/session",
    badge: "Recommended",
    badgeVariant: "secondary" as const,
  },
  {
    id: "budget",
    label: "Budget",
    description: "Haiku for all tasks + Deepgram Aura TTS",
    cost: "~$0.15–0.30/session",
    badge: "Cheapest",
    badgeVariant: "outline" as const,
  },
];

const BYOK_PROVIDERS = [
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    placeholder: "sk-ant-api03-...",
    helpUrl: "https://console.anthropic.com/settings/keys",
    note: "Default LLM provider. Used for all Claude models.",
  },
  {
    id: "openai",
    label: "OpenAI",
    placeholder: "sk-...",
    helpUrl: "https://platform.openai.com/api-keys",
    note: "When set, replaces Claude with your chosen OpenAI model for all LLM tasks.",
  },
  {
    id: "deepgram",
    label: "Deepgram",
    placeholder: "Token ...",
    helpUrl: "https://console.deepgram.com/",
    note: "Speech-to-text provider.",
  },
  {
    id: "elevenlabs",
    label: "ElevenLabs",
    placeholder: "xi-api-key-...",
    helpUrl: "https://elevenlabs.io/app/settings/api-keys",
    note: "Text-to-speech provider (Quality & Balanced profiles).",
  },
];

function SettingsContent() {
  useAuth();

  const router = useRouter();
  const searchParams = useSearchParams();
  const byokRequired = searchParams.get("byok") === "anthropic";

  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingDigest, setSavingDigest] = useState(false);
  const [openaiModel, setOpenaiModel] = useState("");
  const [byokValues, setByokValues] = useState<Record<string, string>>({
    anthropic: "",
    openai: "",
    deepgram: "",
    elevenlabs: "",
  });
  const [savingByok, setSavingByok] = useState(false);
  const [byokError, setByokError] = useState<string | null>(null);
  const [byokSuccess, setByokSuccess] = useState(false);
  const [deletingByok, setDeletingByok] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [testingByok, setTestingByok] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string }>>({});

  useEffect(() => {
    api.settings.get()
      .then((s) => { setSettings(s); setOpenaiModel(s.openai_model ?? "gpt-4o"); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleProfileChange(profile: string) {
    setSavingProfile(true);
    try {
      const updated = await api.settings.patch({ default_quality_profile: profile });
      setSettings(updated);
    } catch {
      // silently fail — user can retry
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleDigestToggle(enabled: boolean) {
    setSavingDigest(true);
    try {
      const updated = await api.settings.patch({ email_digest: enabled });
      setSettings(updated);
    } catch {
      // silently fail
    } finally {
      setSavingDigest(false);
    }
  }

  async function handleByokSave() {
    setSavingByok(true);
    setByokError(null);
    setByokSuccess(false);

    const payload: Record<string, string> = {};
    for (const p of BYOK_PROVIDERS) {
      if (byokValues[p.id] !== "") {
        payload[p.id] = byokValues[p.id];
      }
    }

    if (Object.keys(payload).length === 0) {
      setByokError("Enter at least one API key to save.");
      setSavingByok(false);
      return;
    }

    try {
      const updated = await api.settings.upsertByok(payload);
      setSettings(updated);
      setByokValues({ anthropic: "", openai: "", deepgram: "", elevenlabs: "" });
      setByokSuccess(true);
      setTimeout(() => setByokSuccess(false), 3000);
    } catch (err) {
      setByokError(err instanceof ApiError ? err.message : "Failed to save keys.");
    } finally {
      setSavingByok(false);
    }
  }

  async function handleByokDelete() {
    if (!confirm("Remove all your stored API keys? This cannot be undone.")) return;
    setDeletingByok(true);
    try {
      const updated = await api.settings.deleteByok();
      setSettings(updated);
    } catch {
      // silently fail
    } finally {
      setDeletingByok(false);
    }
  }

  async function handleByokTest(providerId: string) {
    const key = byokValues[providerId];
    if (!key) return;
    setTestingByok((t) => ({ ...t, [providerId]: true }));
    setTestResults((r) => ({ ...r, [providerId]: { ok: false, message: "" } }));
    try {
      const result = await api.settings.testByok(providerId, key);
      setTestResults((r) => ({ ...r, [providerId]: result }));
    } catch {
      setTestResults((r) => ({ ...r, [providerId]: { ok: false, message: "Request failed." } }));
    } finally {
      setTestingByok((t) => ({ ...t, [providerId]: false }));
    }
  }

  if (loading) {
    return (
      <>
        <AppNav />
        <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </main>
      </>
    );
  }

  return (
    <>
      <AppNav />
      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Settings</h1>

        {/* BYOK required banner */}
        {byokRequired && (
          <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-700">
            <AlertTriangle className="text-amber-500 size-4" />
            <AlertTitle className="text-amber-800 dark:text-amber-200">
              Your 2 free sessions have been used
            </AlertTitle>
            <AlertDescription className="text-amber-700 dark:text-amber-300">
              Add your <strong>Anthropic API key</strong> below to continue practising — it powers the AI interviewer.
              Deepgram (speech recognition) and ElevenLabs (voice) remain covered by the platform.
              Get a free key at{" "}
              <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="underline font-medium">
                console.anthropic.com
              </a>.
            </AlertDescription>
          </Alert>
        )}

        {/* ── Quality Profile ────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Default Quality Profile</CardTitle>
            <CardDescription>Sets the default for new sessions. You can override per-session.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {QUALITY_PROFILES.map((p) => {
              const active = settings?.default_quality_profile === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => handleProfileChange(p.id)}
                  disabled={savingProfile}
                  className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
                    active
                      ? "border-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 dark:border-indigo-600 ring-1 ring-indigo-300 dark:ring-indigo-800"
                      : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        active ? "border-indigo-500" : "border-slate-300"
                      }`}>
                        {active && <div className="w-2 h-2 rounded-full bg-indigo-500" />}
                      </div>
                      <span className="font-medium text-slate-800 dark:text-slate-100 text-sm">{p.label}</span>
                      <Badge variant={p.badgeVariant} className="text-xs">
                        {p.badge}
                      </Badge>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">{p.cost}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 ml-6">{p.description}</p>
                </button>
              );
            })}
            {savingProfile && (
              <p className="text-xs text-indigo-500">Saving...</p>
            )}
          </CardContent>
        </Card>

        {/* ── Email Digest ──────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Weekly Practice Digest</CardTitle>
            <CardDescription>
              Receive a weekly email with your skill progress, top areas to improve, and your drill plan for the week.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <Label htmlFor="email-digest" className="text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer">
                Enable weekly digest emails
              </Label>
              <Switch
                id="email-digest"
                checked={settings?.email_digest ?? false}
                onCheckedChange={(checked) => handleDigestToggle(checked)}
                disabled={savingDigest || !settings}
              />
            </div>
            {settings?.email_digest && (
              <p className="mt-3 text-xs text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 rounded-lg px-3 py-2">
                Digest emails are enabled. Configure your SMTP settings in <code className="font-mono">.env</code> to start receiving them.
              </p>
            )}
          </CardContent>
        </Card>

        {/* ── BYOK ──────────────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="size-4 text-slate-500" />
              Bring Your Own Keys (BYOK)
            </CardTitle>
            <CardDescription>
              Use your own API keys. They are encrypted at rest and never logged.
              When set, they replace the platform keys for your sessions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">

            {/* OpenAI model selector */}
            {(settings?.byok_providers.includes("openai") || byokValues.openai !== "") && (
              <div className="bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800 rounded-xl p-4 space-y-3">
                <div>
                  <Label className="text-violet-800 dark:text-violet-300 font-semibold">OpenAI Model</Label>
                  <p className="text-xs text-violet-600 dark:text-violet-400 mt-0.5">
                    Examples: <code className="font-mono">gpt-4o</code>,{" "}
                    <code className="font-mono">gpt-4o-mini</code>,{" "}
                    <code className="font-mono">o3</code>
                  </p>
                </div>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    value={openaiModel}
                    onChange={(e) => setOpenaiModel(e.target.value)}
                    placeholder="gpt-4o"
                    className="flex-1 font-mono border-violet-300 dark:border-violet-700 focus-visible:ring-violet-400/50"
                  />
                  <button
                    onClick={async () => {
                      if (!openaiModel.trim()) return;
                      const updated = await api.settings.patch({ openai_model: openaiModel.trim() });
                      setSettings(updated);
                    }}
                    className="px-3 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors font-medium"
                  >
                    Save
                  </button>
                </div>
                {settings?.openai_model && (
                  <p className="text-xs text-violet-500">
                    Current: <span className="font-mono font-semibold">{settings.openai_model}</span>
                  </p>
                )}
              </div>
            )}

            {/* Active keys summary */}
            {settings && settings.byok_providers.length > 0 && (
              <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-xl p-3 space-y-1.5">
                <p className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wide">Active Keys</p>
                {settings.byok_providers.map((provider) => (
                  <div key={provider} className="flex items-center gap-2 text-sm text-green-800 dark:text-green-300">
                    <CheckCircle2 className="size-3.5 text-green-500 shrink-0" />
                    <span className="font-medium capitalize">{provider}</span>
                    <span className="text-green-600 dark:text-green-500 font-mono text-xs">
                      {settings.byok_key_previews[provider]}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <Separator />

            {/* Key input fields */}
            <div className="space-y-4">
              {BYOK_PROVIDERS.map((p) => (
                <div key={p.id} className="space-y-1.5">
                  <Label htmlFor={`byok-${p.id}`} className="text-slate-700 dark:text-slate-200">
                    {p.label}
                    {settings?.byok_providers.includes(p.id) && (
                      <Badge variant="secondary" className="ml-2 text-xs text-green-700 bg-green-100">
                        Active
                      </Badge>
                    )}
                  </Label>
                  {p.note && (
                    <p className="text-xs text-muted-foreground">{p.note}</p>
                  )}
                  <div className="flex gap-2">
                    <Input
                      id={`byok-${p.id}`}
                      type="password"
                      autoComplete="off"
                      value={byokValues[p.id]}
                      onChange={(e) => {
                        setByokValues((v) => ({ ...v, [p.id]: e.target.value }));
                        setTestResults((r) => { const n = { ...r }; delete n[p.id]; return n; });
                      }}
                      placeholder={
                        settings?.byok_providers.includes(p.id)
                          ? `Current: ${settings.byok_key_previews[p.id]} — paste to update`
                          : p.placeholder
                      }
                      className="flex-1 font-mono"
                    />
                    {byokValues[p.id] && (
                      <button
                        onClick={() => handleByokTest(p.id)}
                        disabled={testingByok[p.id]}
                        className="px-3 py-1.5 text-xs font-medium border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-slate-600 dark:text-slate-300 disabled:opacity-50 whitespace-nowrap"
                      >
                        {testingByok[p.id] ? "Testing…" : "Test"}
                      </button>
                    )}
                    <a
                      href={p.helpUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title={`Get ${p.label} API key`}
                    >
                      <ExternalLink className="size-4" />
                    </a>
                  </div>
                  {testResults[p.id] && (
                    <div className={`flex items-center gap-1.5 text-xs font-medium mt-1 ${
                      testResults[p.id].ok ? "text-emerald-600" : "text-red-500"
                    }`}>
                      {testResults[p.id].ok
                        ? <CheckCircle2 className="size-3.5" />
                        : <XCircle className="size-3.5" />
                      }
                      {testResults[p.id].message}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {byokError && (
              <Alert variant="destructive">
                <XCircle className="size-4" />
                <AlertDescription>{byokError}</AlertDescription>
              </Alert>
            )}
            {byokSuccess && (
              <Alert className="border-green-200 bg-green-50 dark:bg-green-950/30">
                <CheckCircle2 className="size-4 text-green-600" />
                <AlertDescription className="text-green-700 dark:text-green-300">
                  Keys saved successfully.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex gap-3 pt-1">
              <button
                onClick={handleByokSave}
                disabled={savingByok}
                className="btn-primary !py-2 !px-4 !text-sm"
              >
                {savingByok ? "Saving..." : "Save Keys"}
              </button>

              {settings && settings.byok_providers.length > 0 && (
                <button
                  onClick={handleByokDelete}
                  disabled={deletingByok}
                  className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800 transition-colors"
                >
                  {deletingByok ? "Removing..." : "Remove All Keys"}
                </button>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              Keys are encrypted with AES-256 (Fernet) before storage. Leave a field empty to keep the existing key unchanged.
            </p>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-200 dark:border-red-900">
          <CardHeader>
            <CardTitle className="text-red-600 dark:text-red-400">Danger Zone</CardTitle>
            <CardDescription>These actions are permanent and cannot be undone.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Delete Account</p>
                <p className="text-xs text-slate-500 mt-1">
                  Permanently removes your account, all sessions, transcripts, skill data, stories, and API keys.
                  Satisfies your right to erasure under GDPR / CCPA.
                </p>
              </div>
              <button
                onClick={async () => {
                  if (!confirm("Delete your account and ALL data? This cannot be undone.")) return;
                  if (!confirm("Are you absolutely sure? All sessions and skill data will be gone forever.")) return;
                  setDeletingAccount(true);
                  try {
                    await api.settings.deleteAccount();
                    localStorage.removeItem("access_token");
                    router.push("/?deleted=1");
                  } catch {
                    setDeletingAccount(false);
                    alert("Failed to delete account. Please try again or contact privacy@interviewcraft.ai");
                  }
                }}
                disabled={deletingAccount}
                className="shrink-0 px-4 py-2 text-sm font-medium text-red-600 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors disabled:opacity-50"
              >
                {deletingAccount ? "Deleting..." : "Delete Account"}
              </button>
            </div>
          </CardContent>
        </Card>

        <p className="text-xs text-center text-slate-400 pb-4">
          <a href="/privacy" className="hover:underline">Privacy Policy</a>
          {" · "}
          <a href="/tos" className="hover:underline">Terms of Service</a>
          {" · "}
          Questions? <a href="mailto:privacy@interviewcraft.ai" className="hover:underline">privacy@interviewcraft.ai</a>
        </p>
      </main>
    </>
  );
}

// useSearchParams() requires a Suspense boundary for Next.js static generation
export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsContent />
    </Suspense>
  );
}
