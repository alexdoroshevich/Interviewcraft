"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ContributeQuestionRequest, QuestionResponse, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { AppNav } from "@/components/AppNav";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const SESSION_TYPES = [
  { value: "behavioral", label: "Behavioral" },
  { value: "system_design", label: "System Design" },
  { value: "coding_discussion", label: "Coding Discussion" },
  { value: "negotiation", label: "Negotiation" },
  { value: "diagnostic", label: "Diagnostic" },
];

const DIFFICULTIES = [
  { value: "l4", label: "L4 (Junior)" },
  { value: "l5", label: "L5 (Mid-level)" },
  { value: "l6", label: "L6 (Senior)" },
];

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-500",
};

export default function ContributePage() {
  const { ready } = useAuth();

  // Form state
  const [text, setText] = useState("");
  const [type, setType] = useState("behavioral");
  const [difficulty, setDifficulty] = useState("l5");
  const [skillsInput, setSkillsInput] = useState("");
  const [company, setCompany] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // My contributions
  const [contributions, setContributions] = useState<QuestionResponse[]>([]);
  const [loadingContribs, setLoadingContribs] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.questions
      .myContributions()
      .then(setContributions)
      .catch(() => {/* non-fatal */})
      .finally(() => setLoadingContribs(false));
  }, [ready]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (text.trim().length < 10) {
      toast.error("Question must be at least 10 characters.");
      return;
    }

    setSubmitting(true);
    setSuccessMsg(null);
    try {
      const skillsList = skillsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const body: ContributeQuestionRequest = {
        text: text.trim(),
        type,
        difficulty,
        skills_tested: skillsList,
        company: company.trim() || null,
      };

      const res = await api.questions.contribute(body);
      setSuccessMsg(res.message);
      setText("");
      setSkillsInput("");
      setCompany("");

      // Refresh list
      const updated = await api.questions.myContributions();
      setContributions(updated);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to submit question");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <AppNav />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Contribute a Question</h1>
          <p className="text-sm text-slate-500 mt-1">
            Encountered a great interview question? Add it to the bank. Questions are reviewed before going live.
          </p>
        </div>

        {/* Submission form */}
        <Card className="mb-8">
          <CardContent className="py-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Question text */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Question *
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  placeholder="e.g. Tell me about a time you had to make a difficult technical trade-off."
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Type */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Type *</label>
                  <select
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {SESSION_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>

                {/* Difficulty */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Difficulty *</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {DIFFICULTIES.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Skills tested */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Skills tested <span className="text-slate-400 font-normal">(comma-separated)</span>
                </label>
                <input
                  type="text"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. star_structure, ownership_signal"
                />
              </div>

              {/* Company */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Company <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. google, meta, amazon"
                />
              </div>

              {successMsg && (
                <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                  {successMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full btn-primary py-2.5 text-sm font-semibold disabled:opacity-50"
              >
                {submitting ? "Submitting…" : "Submit Question"}
              </button>
            </form>
          </CardContent>
        </Card>

        {/* My contributions */}
        <div>
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 border-l-2 border-indigo-500 pl-3 mb-3">
            My Submissions
          </h2>

          {loadingContribs ? (
            <p className="text-sm text-slate-400">Loading…</p>
          ) : contributions.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No submissions yet.</p>
          ) : (
            <div className="space-y-2">
              {contributions.map((q) => (
                <Card key={q.id}>
                  <CardContent className="py-3 flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 dark:text-slate-100 line-clamp-2">{q.text}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-xs text-slate-400 capitalize">{q.type.replace(/_/g, " ")}</span>
                        <span className="text-xs text-slate-300">·</span>
                        <span className="text-xs text-slate-400 uppercase">{q.difficulty}</span>
                        {q.company && (
                          <>
                            <span className="text-xs text-slate-300">·</span>
                            <span className="text-xs text-slate-400 capitalize">{q.company}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <Badge className={`${STATUS_STYLES[q.status ?? "pending"] ?? ""} border-transparent shrink-0 text-xs`}>
                      {q.status ?? "pending"}
                    </Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        <p className="text-xs text-slate-400 mt-8 text-center">
          <Link href="/sessions" className="hover:underline">← Back to sessions</Link>
        </p>
      </div>
    </main>
  );
}
