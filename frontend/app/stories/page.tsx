"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, StoryResponse, CoverageMapResponse, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle } from "lucide-react";

// ── Coverage Map ──────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: "strong" | "weak" | "gap" }) {
  const color = status === "strong" ? "bg-green-500" : status === "weak" ? "bg-yellow-400" : "bg-red-500";
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 mt-0.5 ${color}`} />;
}

function CoverageMap({ data }: { data: CoverageMapResponse }) {
  const STATUS_COLOR = {
    strong: "bg-green-100 text-green-800 border-green-200 dark:bg-green-950/30 dark:text-green-300 dark:border-green-800",
    weak: "bg-yellow-50 text-yellow-800 border-yellow-200 dark:bg-yellow-950/30 dark:text-yellow-300 dark:border-yellow-800",
    gap: "bg-red-50 text-red-600 border-red-200 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800",
  };

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
            Coverage Map
          </h2>
          <span className="text-xs text-muted-foreground">
            {data.covered}/{data.competencies.length} covered · {data.coverage_pct}%
          </span>
        </div>

        <Progress value={data.coverage_pct} className="h-2 mb-4" />

        <div className="space-y-2">
          {data.competencies.map((c) => (
            <div key={c.competency} className={`rounded-lg border px-3 py-2 ${STATUS_COLOR[c.status]}`}>
              <div className="flex items-start gap-2 w-full">
                <StatusDot status={c.status} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">
                    {c.competency.replace(/_/g, " ")}
                    {c.story_count > 0 && (
                      <span className="ml-2 text-xs opacity-70">— {c.story_count} stor{c.story_count !== 1 ? "ies" : "y"}</span>
                    )}
                  </span>
                  {c.action && (
                    <p className="text-xs mt-0.5 opacity-80">{c.action}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Story card ────────────────────────────────────────────────────────────────

function StoryCard({ story, onDelete }: { story: StoryResponse; onDelete: (id: string) => void }) {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{story.title}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{story.summary}</p>
          </div>
          {story.best_score_with_this_story !== null && (
            <span className={`text-sm font-bold font-mono shrink-0 ${
              story.best_score_with_this_story >= 80 ? "text-green-600" :
              story.best_score_with_this_story >= 60 ? "text-yellow-600" : "text-red-500"
            }`}>{story.best_score_with_this_story}</span>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 mt-2">
          {story.competencies.map((c) => (
            <Badge key={c} variant="outline" className="text-xs bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/30 dark:text-indigo-300 dark:border-indigo-800">
              {c.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>

        {story.warnings.length > 0 && (
          <Alert className="mt-2 border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800">
            <AlertTriangle className="size-3 text-amber-600" />
            <AlertDescription className="text-xs text-amber-800 dark:text-amber-300">
              {story.warnings.join(" · ")}
            </AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-between mt-3 pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">Used {story.times_used}x</p>
          <button
            onClick={() => onDelete(story.id)}
            className="text-xs text-red-400 hover:text-red-600 transition-colors"
          >
            Delete
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Add story form ────────────────────────────────────────────────────────────

const ALL_COMPETENCIES = [
  "technical_leadership", "execution", "cross_team", "conflict_resolution",
  "mentoring", "failure_recovery", "innovation", "communication",
  "data_driven_decision", "customer_focus",
];

function AddStoryForm({ onCreated }: { onCreated: (story: StoryResponse) => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleComp = (c: string) =>
    setSelected((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]);

  async function handleSubmit() {
    if (!title.trim() || !summary.trim() || selected.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const story = await api.stories.create({ title, summary, competencies: selected });
      onCreated(story);
      setTitle(""); setSummary(""); setSelected([]); setOpen(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save story");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return (
    <button
      onClick={() => setOpen(true)}
      className="w-full py-3 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-400 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
    >
      + Add story manually
    </button>
  );

  return (
    <Card className="border-indigo-200 dark:border-indigo-800">
      <CardContent className="py-4 space-y-3">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">New Story</h3>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title (e.g. Database Migration at Startup X)"
        />
        <Textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          placeholder="One-line summary: Led [what] for [context/outcome]"
          className="resize-none"
        />
        <div>
          <p className="text-xs text-muted-foreground mb-1.5">Competencies demonstrated (pick 1-3)</p>
          <div className="flex flex-wrap gap-1.5">
            {ALL_COMPETENCIES.map((c) => (
              <button key={c} onClick={() => toggleComp(c)}
                className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                  selected.includes(c)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-indigo-300"
                }`}>{c.replace(/_/g, " ")}</button>
            ))}
          </div>
        </div>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="flex gap-2">
          <button onClick={() => setOpen(false)} className="flex-1 btn-secondary py-2 text-sm">Cancel</button>
          <button onClick={handleSubmit} disabled={loading || !title || !summary || selected.length === 0}
            className="flex-1 btn-primary py-2 text-sm">
            {loading ? "Saving…" : "Save Story"}
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StoriesPage() {
  const { ready } = useAuth();
  const [stories, setStories] = useState<StoryResponse[]>([]);
  const [coverage, setCoverage] = useState<CoverageMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    Promise.all([api.stories.list(), api.stories.coverage()])
      .then(([s, c]) => { setStories(s); setCoverage(c); })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [ready]);

  async function handleDelete(id: string) {
    if (!confirm("Delete this story? This cannot be undone.")) return;
    try {
      await api.stories.delete(id);
      setStories((prev) => prev.filter((s) => s.id !== id));
    } catch {
      alert("Failed to delete story. Please try again.");
    }
  }

  if (loading) return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />
      <div className="w-full max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6 space-y-3">
        <Skeleton className="h-10 w-full rounded-xl" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
      </div>
    </main>
  );

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />

      <div className="w-full max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="stories" className="gap-6">
          <TabsList className="w-full">
            <TabsTrigger value="stories" className="flex-1">My Stories</TabsTrigger>
            <TabsTrigger value="coverage" className="flex-1">Coverage Map</TabsTrigger>
          </TabsList>

          <TabsContent value="stories" className="space-y-3 animate-fade-in">
            <AddStoryForm onCreated={(s) => setStories((prev) => [s, ...prev])} />
            {stories.length === 0 ? (
              <p className="text-center text-muted-foreground text-sm py-8">
                No stories yet. Complete sessions and save detected stories, or add one manually.
              </p>
            ) : (
              stories.map((s) => <StoryCard key={s.id} story={s} onDelete={handleDelete} />)
            )}
          </TabsContent>

          <TabsContent value="coverage" className="animate-fade-in">
            {coverage && <CoverageMap data={coverage} />}
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
