"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, DashboardResponse, ApiError, UserResponse, ResumeProfile, ResumeProfileResponse, InterviewDateResponse } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";

const TYPE_LABELS: Record<string, string> = {
  behavioral: "Behavioral", system_design: "System Design",
  coding_discussion: "Coding", negotiation: "Negotiation", diagnostic: "Diagnostic",
};

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function ReadinessMeter({ score }: { score: number }) {
  const label = score >= 70 ? "Interview Ready" : score >= 50 ? "Getting There" : "Keep Practicing";
  const badgeClass = score >= 70
    ? "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-300"
    : score >= 50
    ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-300"
    : "bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400";

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-muted-foreground font-medium">Readiness Estimate</p>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeClass}`}>{label}</span>
        </div>
        <div className="flex items-center gap-3">
          <Progress value={score} className="flex-1 h-2.5" />
          <span className="text-lg font-bold text-slate-800 dark:text-slate-100 w-12 text-right">{score}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1.5">
          Based on skill scores, session count, and story coverage
        </p>
      </CardContent>
    </Card>
  );
}

function ProfileSection() {
  const [profile, setProfile] = useState<ResumeProfile | null>(null);
  const [hasResume, setHasResume] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.resume.getProfile()
      .then((res: ResumeProfileResponse) => {
        setProfile(res.profile);
        setHasResume(res.has_resume);
      })
      .catch(() => { /* Profile not available yet — that is fine */ })
      .finally(() => setLoadingProfile(false));
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const result = await api.resume.upload(file);
      setProfile(result.profile);
      setHasResume(true);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (loadingProfile) {
    return (
      <Card>
        <CardContent className="py-4 space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-violet-500 pl-3">
            Profile
          </h2>
          <label className={`text-xs font-medium px-3 py-1.5 rounded-lg cursor-pointer transition-colors ${
            uploading
              ? "bg-slate-100 text-slate-400 cursor-wait dark:bg-slate-800"
              : "bg-indigo-50 text-indigo-600 hover:bg-indigo-100 dark:bg-indigo-950/30 dark:text-indigo-400 dark:hover:bg-indigo-900/30"
          }`}>
            {uploading ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="size-3 animate-spin" />
                Parsing...
              </span>
            ) : hasResume ? "Re-upload Resume" : "Upload Resume"}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        </div>

        {uploadError && (
          <Alert variant="destructive" className="mb-2">
            <AlertDescription className="text-xs">{uploadError}</AlertDescription>
          </Alert>
        )}

        {profile ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-4 text-sm">
              {profile.target_role && (
                <div>
                  <p className="text-xs text-muted-foreground">Target Role</p>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{profile.target_role}</p>
                </div>
              )}
              {profile.target_level && (
                <div>
                  <p className="text-xs text-muted-foreground">Level</p>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{profile.target_level}</p>
                </div>
              )}
              {profile.target_company && (
                <div>
                  <p className="text-xs text-muted-foreground">Target Company</p>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{profile.target_company}</p>
                </div>
              )}
              {profile.experience_years !== null && (
                <div>
                  <p className="text-xs text-muted-foreground">Experience</p>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{profile.experience_years} years</p>
                </div>
              )}
            </div>

            {profile.skills.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1.5">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.skills.slice(0, 12).map((skill) => (
                    <Badge key={skill} variant="outline" className="text-xs bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/30 dark:text-indigo-300 dark:border-indigo-800">
                      {skill}
                    </Badge>
                  ))}
                  {profile.skills.length > 12 && (
                    <Badge variant="secondary" className="text-xs">
                      +{profile.skills.length - 12} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {profile.experience_summary && (
              <p className="text-xs text-muted-foreground leading-relaxed">{profile.experience_summary}</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Upload your resume to auto-fill your profile and get personalized interview practice.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { ready } = useAuth();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasAssessment, setHasAssessment] = useState(true);
  const [interviewDate, setInterviewDate] = useState<InterviewDateResponse | null>(null);
  const [dateUpdating, setDateUpdating] = useState(false);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      api.dashboard.get(),
      api.auth.me(),
      api.profile.getSelfAssessment().catch(() => ({ completed: false, data: null })),
      api.profile.getInterviewDate().catch(() => null),
    ])
      .then(([dashData, userData, saStatus, dateData]) => {
        setData(dashData);
        setUser(userData);
        setHasAssessment(saStatus.completed);
        setInterviewDate(dateData);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, [ready]);

  async function handleDateChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value || null;
    setDateUpdating(true);
    try {
      const updated = await api.profile.setInterviewDate(val);
      setInterviewDate(updated);
    } catch { /* silent — date is non-critical */ }
    finally { setDateUpdating(false); }
  }

  if (loading) return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />
      <div className="max-w-3xl mx-auto px-4 py-6 grid grid-cols-2 gap-3">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
    </main>
  );

  if (error || !data) return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
      <Alert variant="destructive" className="max-w-sm">
        <AlertDescription>{error ?? "Failed to load"}</AlertDescription>
      </Alert>
    </main>
  );

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Welcome back{user ? `, ${user.email}` : ""}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">Here&apos;s your practice overview</p>
        </div>

        {/* Interview Countdown */}
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Target Interview Date</p>
                {interviewDate?.days_until !== null && interviewDate?.days_until !== undefined ? (
                  <p className="text-lg font-bold text-indigo-700 dark:text-indigo-400">
                    {interviewDate.days_until === 0
                      ? "Today!"
                      : `${interviewDate.days_until} day${interviewDate.days_until === 1 ? "" : "s"} away`}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">Not set — add a date to get an urgency-aware drill plan</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {dateUpdating && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
                <input
                  type="date"
                  value={interviewDate?.interview_date ?? ""}
                  min={new Date().toISOString().split("T")[0]}
                  onChange={handleDateChange}
                  className="text-sm border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {!hasAssessment && (
          <Link
            href="/onboarding"
            className="block bg-gradient-to-r from-indigo-500 to-violet-500 rounded-2xl p-5 text-white hover:from-indigo-600 hover:to-violet-600 transition-all"
          >
            <p className="font-semibold mb-1">Complete your practice profile</p>
            <p className="text-sm text-white/80">
              Tell us your target company, level, and weak areas to get personalized drill plans.
            </p>
            <span className="inline-block mt-2 text-sm font-medium bg-white/20 px-3 py-1 rounded-lg">
              Set up profile →
            </span>
          </Link>
        )}

        <ProfileSection />

        {data.readiness_estimate !== null && (
          <ReadinessMeter score={data.readiness_estimate} />
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Sessions" value={data.total_sessions} sub={`${data.sessions_last_30_days} last 30d`} />
          <StatCard label="Avg Score" value={data.avg_score_all_time?.toFixed(1) ?? "—"} sub={`Best: ${data.best_session_score ?? "—"}`} />
          <StatCard label="Skills Tracked" value={data.total_skills_tracked} sub={`Avg: ${data.avg_skill_score?.toFixed(0) ?? "—"}`} />
          <StatCard label="Stories" value={data.total_stories} sub={`${data.coverage_pct}% covered`} />
        </div>

        {data.total_skills_tracked > 0 && (
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
                  Skill Snapshot
                </h2>
                <Link href="/skills" className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline">
                  View full graph →
                </Link>
              </div>
              <div className="flex gap-6 text-sm">
                {data.weakest_skill && (
                  <div>
                    <p className="text-xs text-muted-foreground">Weakest</p>
                    <p className="text-red-500 font-medium">{data.weakest_skill.replace(/_/g, " ")}</p>
                  </div>
                )}
                {data.strongest_skill && (
                  <div>
                    <p className="text-xs text-muted-foreground">Strongest</p>
                    <p className="text-green-600 font-medium">{data.strongest_skill.replace(/_/g, " ")}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {data.total_negotiation_sessions > 0 && (
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
                  Negotiation Training
                </h2>
                <Link href="/negotiation" className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline">
                  History →
                </Link>
              </div>
              <div className="flex gap-6 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Sessions</p>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{data.total_negotiation_sessions}</p>
                </div>
                {data.avg_negotiation_score !== null && (
                  <div>
                    <p className="text-xs text-muted-foreground">Avg Score</p>
                    <p className="font-medium text-slate-800 dark:text-slate-100">{data.avg_negotiation_score}</p>
                  </div>
                )}
                {data.avg_money_left_on_table !== null && (
                  <div>
                    <p className="text-xs text-muted-foreground">Avg Left on Table</p>
                    <p className="font-medium text-red-500">${data.avg_money_left_on_table.toLocaleString()}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="py-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2 border-l-2 border-indigo-500 pl-3">
              API Cost
            </h2>
            <div className="flex gap-6 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Total</p>
                <p className="font-mono font-medium text-slate-800 dark:text-slate-100">${data.total_cost_usd.toFixed(3)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last 30 days</p>
                <p className="font-mono font-medium text-slate-800 dark:text-slate-100">${data.cost_last_30_days.toFixed(3)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {data.recent_sessions.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3">
                Recent Sessions
              </h2>
              <Link href="/sessions" className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline">
                All sessions →
              </Link>
            </div>
            <div className="space-y-2">
              {data.recent_sessions.map((s) => (
                <Link
                  key={s.id}
                  href={`/sessions/${s.id}/transcript`}
                  className="block"
                >
                  <Card className="hover:border-indigo-200 dark:hover:border-indigo-700 transition-colors">
                    <CardContent className="py-3 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{TYPE_LABELS[s.type] ?? s.type}</p>
                        <p className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        {s.avg_score !== null && (
                          <span className={`text-sm font-bold font-mono ${
                            s.avg_score >= 80 ? "text-green-600" :
                            s.avg_score >= 60 ? "text-yellow-600" : "text-red-500"
                          }`}>{s.avg_score}</span>
                        )}
                        <Badge variant={s.status === "active" ? "default" : "secondary"} className="text-xs">
                          {s.status}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        )}

        {data.total_sessions === 0 && (
          <Card className="bg-indigo-50 border-indigo-200 dark:bg-indigo-950/30 dark:border-indigo-800">
            <CardContent className="py-6 text-center">
              <p className="text-indigo-800 dark:text-indigo-300 font-medium mb-2">Ready to start practicing?</p>
              <p className="text-sm text-indigo-700 dark:text-indigo-400 mb-4">
                Complete your first interview session to build your skill graph and track progress.
              </p>
              <Link href="/sessions/new" className="btn-primary inline-flex items-center">
                Start First Session →
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
