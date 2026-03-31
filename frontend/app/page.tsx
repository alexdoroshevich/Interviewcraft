import Link from "next/link";

function IconMic() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function IconMagnifier() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconRewind() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 .49-3.87" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function IconFolder() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconDollar() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-indigo-500">
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}

function Feature({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="card p-4 sm:p-6 hover:shadow-md transition-shadow">
      <div className="w-9 h-9 bg-indigo-50 dark:bg-indigo-950/50 rounded-xl flex items-center justify-center mb-3">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1.5">{title}</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{desc}</p>
    </div>
  );
}

function LoopStep({ n, label }: { n: number; label: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-white text-xs font-bold flex items-center justify-center shrink-0 shadow-sm shadow-indigo-200">
        {n}
      </span>
      <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-900">
      {/* Beta banner */}
      <div className="bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800/60 px-4 py-2.5 text-center">
        <p className="text-xs sm:text-sm text-amber-800 dark:text-amber-300 font-medium">
          Early access — InterviewCraft is actively in development. New interview types and professions are being added.{" "}
          <span className="font-semibold">Expect improvements every week.</span>
        </p>
      </div>

      {/* Nav */}
      <nav className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/60 px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <span className="text-base sm:text-lg font-bold gradient-text">InterviewCraft</span>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/login" className="btn-secondary px-3 sm:px-4 py-2 text-sm min-h-[44px] flex items-center">
            Log in
          </Link>
          <Link href="/login" className="btn-primary px-3 sm:px-4 py-2 text-sm min-h-[44px] flex items-center">
            Start free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-24 text-center animate-fade-in">
        <div className="inline-block bg-indigo-50 text-indigo-600 text-xs font-semibold px-3 py-1.5 rounded-full border border-indigo-100 mb-5 sm:mb-6">
          Deliberate Practice Engine for Tech Interviews
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 dark:text-slate-100 leading-tight mb-4 sm:mb-5">
          Stop practicing blindly.<br />
          <span className="gradient-text">See exactly what to fix.</span>
        </h1>
        <p className="text-base sm:text-lg text-slate-500 mb-8 sm:mb-10 max-w-2xl mx-auto leading-relaxed">
          AI voice interviewer that scores every answer with evidence-backed feedback,
          rewrites your answer three ways, tracks 22 microskills over time,
          and builds a personalized drill plan.
        </p>
        <div className="flex gap-3 justify-center flex-wrap">
          <Link href="/login" className="btn-primary px-5 sm:px-7 py-3 sm:py-3.5 text-sm sm:text-base shadow-lg shadow-indigo-200/50">
            Start practicing free
          </Link>
          <Link href="/dashboard" className="btn-secondary px-5 sm:px-7 py-3 sm:py-3.5 text-sm sm:text-base shadow-sm">
            View dashboard
          </Link>
        </div>
        <p className="text-xs text-slate-400 mt-5">
          No credit card required. 2 free sessions included — then add your own API keys to continue.
        </p>
      </section>

      {/* The loop */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-12 sm:pb-16">
        <div className="card p-5 sm:p-8">
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-6 text-center">
            The Closed Training Loop
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 stagger-children">
            <LoopStep n={1} label="Answer by voice" />
            <LoopStep n={2} label="Lint with evidence" />
            <LoopStep n={3} label="See 3 rewrites" />
            <LoopStep n={4} label="Rewind + re-answer" />
            <LoopStep n={5} label="Delta score shown" />
            <LoopStep n={6} label="Skill graph updates" />
            <LoopStep n={7} label="Drill plan adapts" />
            <LoopStep n={8} label="Next weakness drilled" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-14 sm:pb-20">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-5 sm:mb-6 text-center">
          Built Different
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 stagger-children">
          <Feature icon={<IconMic />} title="Real-time Voice" desc="VAD-aware pipeline with Deepgram Nova-2 + ElevenLabs. No typing. Target p95 &lt; 2s." />
          <Feature icon={<IconMagnifier />} title="Evidence-backed Scoring" desc="15-rule rubric. Every triggered rule links to the exact moment you said it." />
          <Feature icon={<IconRewind />} title="Rewind Micro-Practice" desc="Re-answer weak questions. See the delta: +12 in structure, -3 in depth." />
          <Feature icon={<IconChart />} title="Skill Graph Memory" desc="22 microskills tracked across every session. Spaced repetition for weak areas." />
          <Feature icon={<IconFolder />} title="Story Bank" desc="Auto-detect STAR stories. Coverage map shows gaps. Overuse warnings." />
          <Feature icon={<IconDollar />} title="Negotiation Simulator" desc="AI recruiter with hidden max budget. Scores anchoring and emotional control." />
        </div>
      </section>

      {/* How pricing works */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-14 sm:pb-20">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-5 sm:mb-6 text-center">
          Transparent Pricing
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Free tier */}
          <div className="card p-5 sm:p-6 border-2 border-indigo-200 dark:border-indigo-800">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Free to start</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">
              Every new account includes <strong className="text-slate-700 dark:text-slate-200">2 complete interview sessions</strong> at no cost. No credit card. No hidden charges.
            </p>
            <ul className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400">
              <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">✓</span> Full voice pipeline with scoring</li>
              <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">✓</span> Skill graph and drill plan</li>
              <li className="flex items-start gap-1.5"><span className="text-emerald-500 mt-0.5">✓</span> All session types included</li>
            </ul>
          </div>
          {/* BYOK */}
          <div className="card p-5 sm:p-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-indigo-500 shrink-0"></span>
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Bring Your Own Keys</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">
              After your 2 free sessions, add your own API keys in <strong className="text-slate-700 dark:text-slate-200">Settings → API Keys</strong>. You pay the AI providers directly at their published rates — typically <strong className="text-slate-700 dark:text-slate-200">~$0.10–0.40 per session</strong>.
            </p>
            <ul className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400">
              <li className="flex items-start gap-1.5"><span className="text-indigo-400 mt-0.5">→</span> Anthropic Claude (voice + scoring)</li>
              <li className="flex items-start gap-1.5"><span className="text-indigo-400 mt-0.5">→</span> Deepgram (speech-to-text)</li>
              <li className="flex items-start gap-1.5"><span className="text-indigo-400 mt-0.5">→</span> ElevenLabs (text-to-speech, optional)</li>
            </ul>
          </div>
        </div>
        <p className="text-center text-xs text-slate-400 mt-4">
          Your API keys are encrypted at rest and never logged or shared. You can delete them at any time.
        </p>
      </section>

      {/* Coming soon */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-14 sm:pb-20">
        <div className="card p-5 sm:p-8 bg-gradient-to-br from-indigo-50/50 to-violet-50/50 dark:from-indigo-950/20 dark:to-violet-950/20 border border-indigo-100 dark:border-indigo-900/50">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 text-xs font-semibold px-2.5 py-1 rounded-full border border-violet-200 dark:border-violet-800">
              Coming Soon
            </span>
          </div>
          <h2 className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
            Built for every profession — not just tech
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-5">
            InterviewCraft starts with software engineering. We are building interview prep for every career — from operating rooms to courtrooms to trading floors. Each profession gets its own question bank, scoring rubric, and interviewer persona.
          </p>

          <div className="space-y-4">
            {/* Tech expansion */}
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Tech & Engineering</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5">
                {[
                  ["Product Management", "Case studies, metrics, prioritization"],
                  ["Data Science / ML", "SQL, statistics, model design"],
                  ["Engineering Manager", "People leadership, org design"],
                  ["DevOps / SRE", "Incident response, reliability"],
                  ["Security Engineer", "Threat modeling, pen testing"],
                  ["Frontend / Mobile", "DOM, performance, accessibility"],
                  ["Data Engineering", "Pipelines, warehousing, Spark"],
                  ["UX Research", "Study design, synthesis, stakeholders"],
                ].map(([title, sub]) => (
                  <div key={title} className="bg-white/60 dark:bg-slate-800/40 rounded-xl p-2.5 border border-slate-200/60 dark:border-slate-700/40">
                    <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{title}</p>
                    <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">{sub}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Business & finance */}
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Business & Finance</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5">
                {[
                  ["Management Consulting", "Case interviews, market sizing, frameworks"],
                  ["Investment Banking", "DCF, LBO, deal structuring, fit questions"],
                  ["Financial Analyst", "Valuation, modeling, markets, EBITDA"],
                  ["Accounting / Audit", "GAAP, Big 4 controls, compliance, CPA"],
                  ["Sales & Account Mgmt", "Discovery, objection handling, quotas"],
                  ["Operations / Supply Chain", "Lean, logistics, ERP, procurement"],
                  ["Marketing Manager", "Campaign strategy, analytics, ROI"],
                  ["HR / Talent Acquisition", "Recruitment strategy, sourcing, HRBP"],
                ].map(([title, sub]) => (
                  <div key={title} className="bg-white/60 dark:bg-slate-800/40 rounded-xl p-2.5 border border-slate-200/60 dark:border-slate-700/40">
                    <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{title}</p>
                    <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">{sub}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Healthcare */}
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Healthcare & Medicine</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5">
                {[
                  ["Physician / Resident", "MMI ethics, clinical reasoning, AAMC"],
                  ["Dentist / Dental School", "MMI scenarios, patient communication"],
                  ["Registered Nurse", "Patient safety, NCLEX scenarios, STAR"],
                  ["Pharmacist", "Drug interactions, clinical counseling"],
                  ["Physical Therapist", "Clinical scenarios, patient assessment"],
                  ["Social Worker", "Ethics, case scenarios, NASW standards"],
                ].map(([title, sub]) => (
                  <div key={title} className="bg-white/60 dark:bg-slate-800/40 rounded-xl p-2.5 border border-slate-200/60 dark:border-slate-700/40">
                    <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{title}</p>
                    <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">{sub}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Legal & Education */}
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Legal, Education & Public Sector</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5">
                {[
                  ["Attorney / Lawyer", "Case analysis, ethics, law firm fit"],
                  ["Paralegal", "Legal research, drafting, e-discovery"],
                  ["Teacher / Educator", "Classroom management, differentiation"],
                  ["Academic Researcher", "Grant proposals, peer review, funding"],
                  ["Government / Policy", "Competency-based, OPM framework"],
                ].map(([title, sub]) => (
                  <div key={title} className="bg-white/60 dark:bg-slate-800/40 rounded-xl p-2.5 border border-slate-200/60 dark:border-slate-700/40">
                    <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{title}</p>
                    <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">{sub}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <p className="text-center text-xs text-slate-400 mt-5">
            Every profession listed has a verified question bank. More roles added weekly.
          </p>
        </div>
      </section>

      {/* Demo video */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-14 sm:pb-20">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-5 sm:mb-6 text-center">
          See It In Action
        </h2>
        <div className="aspect-video bg-slate-900 rounded-2xl flex flex-col items-center justify-center border border-slate-800 shadow-xl">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-14 h-14 text-indigo-400 mb-4 opacity-60">
            <path fillRule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm14.024-.983a1.125 1.125 0 010 1.966l-5.603 3.113A1.125 1.125 0 019 15.113V8.887c0-.857.921-1.4 1.671-.983l5.603 3.113z" clipRule="evenodd" />
          </svg>
          <p className="text-slate-400 text-sm font-medium">3-minute demo video — coming soon</p>
          <p className="text-slate-600 text-xs mt-1">Full closed-loop walkthrough: voice → lint → diff → rewind → skill graph</p>
        </div>
      </section>

      {/* KPI strip */}
      <section className="bg-gradient-to-r from-indigo-600 to-violet-600 py-10 sm:py-16">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
          <p className="text-indigo-200 text-sm font-medium mb-2">Design Targets</p>
          <h2 className="text-xl sm:text-2xl font-bold text-white mb-6 sm:mb-8">Measurable goals, not vibes</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 text-sm">
            {[
              ["< 2s", "voice latency p95"],
              ["< 8 pts", "scoring variance"],
              ["> 60%", "cache hit rate"],
              ["+8 avg", "rewind delta"],
            ].map(([val, label]) => (
              <div key={label} className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/10">
                <p className="text-xl font-bold text-white font-mono">{val}</p>
                <p className="text-indigo-200 text-xs mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-2xl mx-auto px-4 sm:px-6 py-12 sm:py-20 text-center">
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 mb-3">Ready to close the loop?</h2>
        <p className="text-sm sm:text-base text-slate-500 mb-2 sm:mb-3">
          Your first diagnostic session is 5 minutes. It seeds your skill graph and tells you exactly what to practice next.
        </p>
        <p className="text-xs text-slate-400 mb-6 sm:mb-8">
          2 sessions free. No credit card. After that, add your own API keys in Settings.
        </p>
        <Link href="/login" className="btn-primary inline-flex items-center px-6 sm:px-8 py-3 sm:py-3.5 text-base sm:text-lg shadow-lg shadow-indigo-200/50">
          Start your first session free
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-900/50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-10 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
          <span className="text-sm font-semibold gradient-text">InterviewCraft</span>
          <div className="flex items-center gap-4 sm:gap-6 text-xs text-slate-400">
            <Link href="/tos" className="py-2 px-1 hover:text-slate-600 hover:underline transition-colors min-h-[44px] flex items-center">Terms</Link>
            <Link href="/privacy" className="py-2 px-1 hover:text-slate-600 hover:underline transition-colors min-h-[44px] flex items-center">Privacy</Link>
            <Link href="/admin/metrics" className="py-2 px-1 hover:text-slate-600 hover:underline transition-colors min-h-[44px] flex items-center">Admin</Link>
          </div>
          <p className="text-xs text-slate-400">&copy; {new Date().getFullYear()} InterviewCraft</p>
        </div>
      </footer>
    </main>
  );
}
