"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  api,
  SkillGraphResponse,
  DrillPlanResponse,
  BeatYourBestItem,
  SkillHistoryResponse,
  SkillHistoryPoint,
  ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { SkillRadar, SkillList } from "@/components/SkillRadar";
import { BeatYourBest } from "@/components/BeatYourBest";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";

// ── Drill plan ────────────────────────────────────────────────────────────────

function DrillPlanSection({ plan }: { plan: DrillPlanResponse }) {
  const TREND_ICON: Record<string, string> = {
    improving: "↑",
    declining: "↓",
    stable: "→",
  };

  const TREND_COLOR: Record<string, string> = {
    improving: "text-green-600",
    declining: "text-red-500",
    stable: "text-slate-400",
  };

  if (plan.message || plan.slots.length === 0) {
    return (
      <Alert className="border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800">
        <AlertTriangle className="size-4 text-amber-600" />
        <AlertDescription className="text-amber-800 dark:text-amber-300">
          {plan.message ?? "No drill plan yet. Score a session to get personalized practice."}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          ~{plan.estimated_minutes_per_week} min/week · {plan.slots.length} sessions
        </p>
        {plan.weakest_skill && (
          <p className="text-xs text-red-500 font-medium">
            Weakest: {plan.weakest_skill.replace(/_/g, " ")}
          </p>
        )}
      </div>

      {plan.slots.map((slot) => (
        <Card key={slot.day} size="sm">
          <CardContent className="py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-500 w-24 shrink-0">{slot.day}</span>
                  <span className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {slot.skill_name.replace(/_/g, " ")}
                  </span>
                  <span className={`text-xs font-bold ${TREND_COLOR[slot.trend] ?? "text-slate-400"}`}>
                    {TREND_ICON[slot.trend] ?? "→"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1.5 ml-[100px]">{slot.focus_note}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs font-mono text-slate-600 dark:text-slate-400">{slot.current_score}/100</p>
                <p className="text-xs text-slate-400 mt-0.5">{slot.questions}q · {slot.estimated_minutes}m</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SkillsPage() {
  const { ready } = useAuth();
  const [graph, setGraph] = useState<SkillGraphResponse | null>(null);
  const [plan, setPlan] = useState<DrillPlanResponse | null>(null);
  const [best, setBest] = useState<BeatYourBestItem[]>([]);
  const [historyMap, setHistoryMap] = useState<Record<string, SkillHistoryPoint[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  async function handleShare() {
    setShareLoading(true);
    try {
      const card = await api.share.createCard();
      const url = `${window.location.origin}/share/${card.token}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url);
      toast.success("Share link copied to clipboard!");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to create share link");
    } finally {
      setShareLoading(false);
    }
  }

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      api.skills.getGraph(),
      api.skills.getPlan(),
      api.skills.getBest(),
      api.skills.getHistory(),
    ])
      .then(([g, p, b, h]: [SkillGraphResponse, DrillPlanResponse, BeatYourBestItem[], SkillHistoryResponse[]]) => {
        setGraph(g);
        setPlan(p);
        setBest(b);
        const map: Record<string, SkillHistoryPoint[]> = {};
        for (const item of h) map[item.skill_name] = item.history;
        setHistoryMap(map);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load skill data"))
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <AppNav />
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <Link href="/sessions" className="text-indigo-600 hover:underline text-sm">← Back to sessions</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Stats row */}
        {graph && graph.total_skills > 0 && (
          <Card className="mb-6">
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Skills tracked</p>
                  <p className="text-xl font-bold text-slate-800 dark:text-slate-100 mt-0.5">{graph.total_skills}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Avg score</p>
                  <p className="text-xl font-bold text-indigo-700 dark:text-indigo-400 mt-0.5">{graph.avg_score}</p>
                </div>
                {graph.weakest_category && (
                  <div>
                    <p className="text-xs text-muted-foreground">Weakest area</p>
                    <p className="text-sm font-semibold text-red-500 mt-1">{graph.weakest_category.replace(/_/g, " ")}</p>
                  </div>
                )}
                {graph.strongest_category && (
                  <div>
                    <p className="text-xs text-muted-foreground">Strongest area</p>
                    <p className="text-sm font-semibold text-green-600 mt-1">{graph.strongest_category.replace(/_/g, " ")}</p>
                  </div>
                )}
              </div>
              <div className="shrink-0">
                <button
                  onClick={handleShare}
                  disabled={shareLoading}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:border-indigo-800 dark:text-indigo-300 dark:hover:bg-indigo-900/50 transition-colors font-medium disabled:opacity-50"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13"/>
                  </svg>
                  {shareLoading ? "Generating…" : "Share Progress"}
                </button>
                {shareUrl && (
                  <p className="text-xs text-slate-400 mt-1.5 max-w-[180px] truncate" title={shareUrl}>
                    {shareUrl}
                  </p>
                )}
              </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="graph" className="gap-6">
          <TabsList className="w-full">
            <TabsTrigger value="graph" className="flex-1">Skill Graph</TabsTrigger>
            <TabsTrigger value="plan" className="flex-1">Drill Plan</TabsTrigger>
            <TabsTrigger value="best" className="flex-1">Beat Your Best</TabsTrigger>
          </TabsList>

          <TabsContent value="graph" className="space-y-6 animate-fade-in">
            {!graph || graph.total_skills === 0 ? (
              <Card>
                <CardContent className="py-8 text-center space-y-3">
                  <p className="text-muted-foreground text-sm">No skill data yet.</p>
                  <p className="text-xs text-muted-foreground">
                    Complete an interview session and click &quot;Score Session&quot; to build your skill graph.
                  </p>
                  <Link href="/sessions/new" className="inline-block mt-2 btn-primary text-sm">
                    Start a Session →
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Radar chart — full width */}
                <Card>
                  <CardContent className="py-4">
                    <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 border-l-2 border-indigo-500 pl-3">
                      Category Overview
                    </h2>
                    <SkillRadar
                      nodes={graph.nodes}
                      activeCategory={activeCategory}
                      onCategoryClick={setActiveCategory}
                    />
                    {activeCategory && (
                      <p className="text-center text-xs text-muted-foreground mt-2">
                        Showing <span className="font-semibold text-indigo-500 capitalize">{activeCategory.replace(/_/g, " ")}</span> — click again to show all
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Skill list — below the chart */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 border-l-2 border-indigo-500 pl-3">
                    {activeCategory ? `${activeCategory.replace(/_/g, " ")} Skills` : "All Skills"}
                  </h2>
                  <SkillList
                    nodes={activeCategory ? graph.nodes.filter(n => n.skill_category === activeCategory) : graph.nodes}
                    historyMap={historyMap}
                  />
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="plan" className="space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
                Weekly Drill Plan
              </h2>
              {plan && (
                <p className="text-xs text-muted-foreground">
                  Updated {new Date(plan.generated_at).toLocaleDateString()}
                </p>
              )}
            </div>
            {plan && <DrillPlanSection plan={plan} />}
          </TabsContent>

          <TabsContent value="best" className="space-y-4 animate-fade-in">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
              Beat Your Best
            </h2>
            <BeatYourBest
              items={best}
              onChallenge={(skill) => {
                window.location.href = `/sessions/new?skill=${encodeURIComponent(skill)}`;
              }}
            />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
