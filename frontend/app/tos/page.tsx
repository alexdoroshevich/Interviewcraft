import Link from "next/link";

export const metadata = {
  title: "Terms of Service — InterviewCraft",
  description: "Terms of Service for InterviewCraft",
};

export default function TermsOfServicePage() {
  const effectiveDate = "March 29, 2026";

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <nav className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/60 px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <Link href="/" className="text-base font-bold text-indigo-600 hover:text-indigo-700">
          ← InterviewCraft
        </Link>
      </nav>

      <article className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-16 prose prose-slate dark:prose-invert prose-sm sm:prose-base">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">Terms of Service</h1>
        <p className="text-sm text-slate-500 mb-8">Effective date: {effectiveDate}</p>

        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          By accessing or using InterviewCraft (&quot;the Service&quot;), you agree to be bound by these Terms of Service. Please read them carefully. If you do not agree, do not use the Service.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">1. Description of Service</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          InterviewCraft is an AI-powered interview practice platform. It provides voice-based mock interviews, answer scoring, skill tracking, and personalized drill plans. The Service is currently in early access and is actively being developed.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">2. Accounts and Eligibility</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          You must be at least 16 years of age to use the Service. You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account. You agree to provide accurate information when registering.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">3. What Data We Collect</h2>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>Account information: email address and hashed password</li>
          <li>Session transcripts: the text of your interview answers (not raw audio — audio is never stored)</li>
          <li>Skill scores and history generated from your sessions</li>
          <li>Resume text if you choose to upload a resume</li>
          <li>API usage logs (token counts, latency, cost) — these never contain your answers</li>
          <li>BYOK API keys you provide — stored encrypted at rest, never logged</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">4. How We Use Your Data</h2>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>To provide the Service: score answers, build your skill graph, generate drill plans</li>
          <li>To personalize your experience based on your practice history</li>
          <li>To send optional weekly digest emails if you enable them in Settings</li>
          <li>We do <strong>not</strong> sell your data to third parties</li>
          <li>We do <strong>not</strong> use your transcripts or answers to train AI models without explicit consent</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">5. Voice Recording and Transcription</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          Interview sessions use your microphone. <strong>Audio is never stored to disk or our servers</strong> — it flows directly from your browser to our speech-to-text provider (Deepgram) in real-time and is discarded immediately after transcription. Only the resulting text transcript is saved. By starting a session, you consent to this real-time transcription.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">6. BYOK — Bring Your Own API Keys</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          If you provide your own API keys (Anthropic, Deepgram, ElevenLabs), they are encrypted using AES-256 before storage and are only decrypted in memory during your session. They are never logged or transmitted to any party other than the respective AI provider during your session.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">7. Data Retention</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          Session transcripts and skill data are retained until you delete your account. Word-level timestamps are automatically purged after 14 days. You may request deletion of all your data at any time via Settings → Delete Account.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">8. Free Sessions and Pricing</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          Every new account receives 2 complete interview sessions at no cost. After that, the Service requires you to provide your own AI provider API keys. You pay the AI providers (Anthropic, Deepgram, ElevenLabs) directly at their published rates. InterviewCraft does not charge you for sessions beyond the 2 free ones unless a paid tier is introduced, in which case you will be notified in advance.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">9. Prohibited Use</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">You agree not to:</p>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>Attempt to reverse-engineer, scrape, or extract data from the Service at scale</li>
          <li>Use the Service to generate content for deceptive purposes</li>
          <li>Share account credentials or resell access</li>
          <li>Attempt to circumvent rate limits or abuse the free session allocation</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">10. Disclaimer of Warranties</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          The Service is provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind. We do not guarantee that the AI scoring will be accurate, that the Service will be uninterrupted, or that it will help you pass any specific interview. Use the Service as one tool among many in your preparation.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">11. Limitation of Liability</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          To the maximum extent permitted by law, InterviewCraft shall not be liable for any indirect, incidental, special, or consequential damages arising from your use of the Service.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">12. Changes to These Terms</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          We may update these Terms from time to time. We will notify you by email or in-app notice at least 14 days before material changes take effect. Continued use after that date constitutes acceptance.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">13. Contact</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          Questions about these Terms? Email us at{" "}
          <a href="mailto:legal@interviewcraft.ai" className="text-indigo-600 hover:underline">
            legal@interviewcraft.ai
          </a>
        </p>

        <div className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-700 flex gap-4 text-sm">
          <Link href="/privacy" className="text-indigo-600 hover:underline">Privacy Policy</Link>
          <Link href="/" className="text-slate-400 hover:text-slate-600">← Back to home</Link>
        </div>
      </article>
    </main>
  );
}
