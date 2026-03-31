"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { api, ApiError, SelfAssessmentRequest } from "@/lib/api";

// ── Constants ────────────────────────────────────────────────────────────────

const LEVELS = [
  { value: "L3", label: "L3", desc: "Junior" },
  { value: "L4", label: "L4", desc: "Mid-Level" },
  { value: "L5", label: "L5", desc: "Senior" },
  { value: "L6", label: "L6", desc: "Staff / Principal" },
  { value: "L7", label: "L7", desc: "Distinguished" },
] as const;

const WEAK_AREAS = [
  { value: "star_structure", label: "STAR Structure" },
  { value: "quantifiable_results", label: "Quantifiable Results" },
  { value: "tradeoff_analysis", label: "Tradeoff Analysis" },
  { value: "system_design", label: "System Design" },
  { value: "coding_discussion", label: "Coding & Algorithms" },
  { value: "data_structures", label: "Data Structures" },
  { value: "conciseness", label: "Conciseness" },
  { value: "filler_words", label: "Filler Words" },
  { value: "ownership", label: "Ownership" },
  { value: "scalability_thinking", label: "Scalability Thinking" },
  { value: "leadership", label: "Leadership" },
  { value: "mentoring", label: "Mentoring" },
  { value: "negotiation", label: "Negotiation" },
] as const;

const TIMELINES = [
  { value: "this_week", label: "This week", icon: "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" },
  { value: "2_weeks", label: "2 weeks", icon: "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" },
  { value: "1_month", label: "1 month", icon: "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z" },
  { value: "2_plus_months", label: "2+ months", icon: "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" },
] as const;

const TOTAL_STEPS = 4;

// ── Component ────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const { ready } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [targetCompany, setTargetCompany] = useState("");
  const [targetLevel, setTargetLevel] = useState("");
  const [weakAreas, setWeakAreas] = useState<string[]>([]);
  const [timeline, setTimeline] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleWeakArea(area: string): void {
    setWeakAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  }

  function canAdvance(): boolean {
    switch (step) {
      case 1: return targetCompany.trim().length > 0;
      case 2: return targetLevel !== "";
      case 3: return weakAreas.length > 0;
      case 4: return timeline !== "";
      default: return false;
    }
  }

  async function handleSubmit(): Promise<void> {
    if (!canAdvance()) return;
    setError(null);
    setSubmitting(true);

    const payload: SelfAssessmentRequest = {
      target_company: targetCompany.trim(),
      target_level: targetLevel,
      weak_areas: weakAreas,
      interview_timeline: timeline,
    };

    try {
      await api.profile.saveSelfAssessment(payload);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleNext(): void {
    if (step < TOTAL_STEPS) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  }

  if (!ready) {
    return (
      <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="animate-pulse text-slate-400">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8 animate-fade-in">
          <h1 className="text-2xl font-bold gradient-text mb-1">Set Up Your Practice Profile</h1>
          <p className="text-sm text-slate-500">
            Help us personalize your drill plan. Takes under a minute.
          </p>
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-2 mb-8">
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                i + 1 <= step
                  ? "bg-gradient-to-r from-indigo-500 to-violet-500"
                  : "bg-slate-200"
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="card p-6 sm:p-8 animate-fade-in" key={step}>
          {/* Step 1: Target company */}
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold text-slate-800 mb-1">
                What company are you targeting?
              </h2>
              <p className="text-sm text-slate-500 mb-6">
                We&apos;ll tailor questions to match their interview style.
              </p>
              <input
                type="text"
                value={targetCompany}
                onChange={(e) => setTargetCompany(e.target.value)}
                placeholder="e.g. Google, Meta, Amazon..."
                className="input-field text-base"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter" && canAdvance()) handleNext();
                }}
              />
            </div>
          )}

          {/* Step 2: Target level */}
          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold text-slate-800 mb-1">
                What level are you interviewing for?
              </h2>
              <p className="text-sm text-slate-500 mb-6">
                This shapes the rubric and seniority expectations.
              </p>
              <div className="grid grid-cols-1 gap-3">
                {LEVELS.map((level) => (
                  <button
                    key={level.value}
                    onClick={() => setTargetLevel(level.value)}
                    className={`flex items-center gap-4 px-4 py-3.5 rounded-xl border text-left transition-all ${
                      targetLevel === level.value
                        ? "border-indigo-400 bg-indigo-50 ring-2 ring-indigo-500/20"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <span
                      className={`text-lg font-bold w-10 text-center ${
                        targetLevel === level.value
                          ? "text-indigo-600"
                          : "text-slate-400"
                      }`}
                    >
                      {level.label}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        targetLevel === level.value
                          ? "text-indigo-700"
                          : "text-slate-600"
                      }`}
                    >
                      {level.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Weak areas */}
          {step === 3 && (
            <div>
              <h2 className="text-lg font-semibold text-slate-800 mb-1">
                Where do you need the most practice?
              </h2>
              <p className="text-sm text-slate-500 mb-6">
                Select all that apply. We&apos;ll prioritize these in your drill plan.
              </p>
              <div className="flex flex-wrap gap-2">
                {WEAK_AREAS.map((area) => {
                  const selected = weakAreas.includes(area.value);
                  return (
                    <button
                      key={area.value}
                      onClick={() => toggleWeakArea(area.value)}
                      className={`px-3.5 py-2 rounded-full text-sm font-medium transition-all ${
                        selected
                          ? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-sm shadow-indigo-200/50"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {area.label}
                    </button>
                  );
                })}
              </div>
              {weakAreas.length > 0 && (
                <p className="text-xs text-slate-400 mt-4">
                  {weakAreas.length} area{weakAreas.length !== 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          )}

          {/* Step 4: Timeline */}
          {step === 4 && (
            <div>
              <h2 className="text-lg font-semibold text-slate-800 mb-1">
                When is your interview?
              </h2>
              <p className="text-sm text-slate-500 mb-6">
                We&apos;ll adjust session intensity to fit your timeline.
              </p>
              <div className="grid grid-cols-2 gap-3">
                {TIMELINES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => setTimeline(t.value)}
                    className={`flex flex-col items-center gap-2 px-4 py-5 rounded-xl border text-center transition-all ${
                      timeline === t.value
                        ? "border-indigo-400 bg-indigo-50 ring-2 ring-indigo-500/20"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className={`w-6 h-6 ${
                        timeline === t.value ? "text-indigo-600" : "text-slate-400"
                      }`}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d={t.icon} />
                    </svg>
                    <span
                      className={`text-sm font-medium ${
                        timeline === t.value ? "text-indigo-700" : "text-slate-600"
                      }`}
                    >
                      {t.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <p className="text-sm text-red-600 text-center mt-4">{error}</p>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => step > 1 && setStep(step - 1)}
            disabled={step === 1}
            className="btn-secondary disabled:opacity-30"
          >
            Back
          </button>

          <span className="text-xs text-slate-400">
            Step {step} of {TOTAL_STEPS}
          </span>

          <button
            onClick={handleNext}
            disabled={!canAdvance() || submitting}
            className="btn-primary"
          >
            {submitting
              ? "Saving..."
              : step === TOTAL_STEPS
              ? "Finish"
              : "Next"}
          </button>
        </div>

        {/* Skip link */}
        <div className="text-center mt-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="text-xs text-slate-400 hover:text-slate-500 transition-colors"
          >
            Skip for now
          </button>
        </div>
      </div>
    </main>
  );
}
