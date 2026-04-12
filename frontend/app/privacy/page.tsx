import Link from "next/link";

export const metadata = {
  title: "Privacy Policy — InterviewCraft",
  description: "Privacy Policy for InterviewCraft",
};

export default function PrivacyPolicyPage() {
  const effectiveDate = "March 29, 2026";

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <nav className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/60 px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <Link href="/" className="text-base font-bold text-indigo-600 hover:text-indigo-700">
          ← InterviewCraft
        </Link>
      </nav>

      <article className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-16 prose prose-slate dark:prose-invert prose-sm sm:prose-base">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">Privacy Policy</h1>
        <p className="text-sm text-slate-500 mb-8">Effective date: {effectiveDate}</p>

        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          This Privacy Policy explains how InterviewCraft collects, uses, and protects your personal data. We are committed to being transparent about our practices.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">1. Data We Collect</h2>
        <div className="space-y-3 text-slate-600 dark:text-slate-400">
          <p><strong className="text-slate-700 dark:text-slate-300">Account data:</strong> Your email address and a bcrypt-hashed password. We never store your plain-text password.</p>
          <p><strong className="text-slate-700 dark:text-slate-300">Session transcripts:</strong> The text of your spoken answers during interview sessions. Audio is processed in real-time by our speech-to-text provider and is never stored on our servers or to disk.</p>
          <p><strong className="text-slate-700 dark:text-slate-300">Skill data:</strong> Scores, trends, and history generated from your sessions. This is the core of what makes InterviewCraft useful.</p>
          <p><strong className="text-slate-700 dark:text-slate-300">Resume data:</strong> If you upload a resume, we store the extracted text and a structured profile (role, skills, experience summary). The original file is not retained.</p>
          <p><strong className="text-slate-700 dark:text-slate-300">API keys (BYOK):</strong> If you provide your own API keys, they are encrypted at rest using AES-256 and are only decrypted in memory during your active session. They are never logged or visible to InterviewCraft staff.</p>
          <p><strong className="text-slate-700 dark:text-slate-300">Usage logs:</strong> Token counts, latency, and cost data per API call for billing transparency. These logs do not contain your answers or transcripts — only session IDs and metrics.</p>
        </div>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">2. How We Use Your Data</h2>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>To provide and improve the Service (scoring, skill tracking, drill plans)</li>
          <li>To send weekly email digests if you opt in via Settings</li>
          <li>To display your API usage and cost in your dashboard</li>
          <li>To detect and prevent abuse of the free session allocation</li>
        </ul>
        <p className="text-slate-600 dark:text-slate-400 mt-3">
          We do <strong>not</strong>:
        </p>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>Sell your data to any third party</li>
          <li>Use your transcripts or answers to train AI models without explicit opt-in consent</li>
          <li>Share your data with advertisers</li>
          <li>Use your data for purposes other than operating the Service</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">3. Third-Party Processors</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed mb-3">
          To operate the Service, we send your data to the following processors:
        </p>
        <div className="overflow-x-auto">
          <table className="text-sm w-full border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="text-left py-2 pr-4 font-semibold text-slate-700 dark:text-slate-300">Provider</th>
                <th className="text-left py-2 pr-4 font-semibold text-slate-700 dark:text-slate-300">Purpose</th>
                <th className="text-left py-2 font-semibold text-slate-700 dark:text-slate-300">Data sent</th>
              </tr>
            </thead>
            <tbody className="text-slate-600 dark:text-slate-400">
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-2 pr-4">Anthropic (Claude)</td>
                <td className="py-2 pr-4">AI voice interviewer, scoring, feedback</td>
                <td className="py-2">Transcript text, session context</td>
              </tr>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-2 pr-4">Deepgram</td>
                <td className="py-2 pr-4">Speech-to-text transcription</td>
                <td className="py-2">Real-time audio stream (not stored)</td>
              </tr>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-2 pr-4">ElevenLabs</td>
                <td className="py-2 pr-4">Text-to-speech (AI voice)</td>
                <td className="py-2">Interviewer response text</td>
              </tr>
              <tr>
                <td className="py-2 pr-4">Fly.io / Vercel</td>
                <td className="py-2 pr-4">Hosting and infrastructure</td>
                <td className="py-2">Encrypted data at rest</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-slate-500 dark:text-slate-400 text-xs mt-2">
          If you use BYOK, your API calls go directly to the provider using your own key — InterviewCraft is not a party to those calls.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">4. Data Retention</h2>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>Session transcripts and skill data: retained until you delete your account</li>
          <li>Word-level timestamps: automatically deleted after 14 days</li>
          <li>Email digest logs: not retained (fire-and-forget)</li>
          <li>API usage logs: retained for 90 days for billing transparency, then deleted</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">5. Your Rights (GDPR & CCPA)</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed mb-3">
          Depending on your location, you may have the following rights:
        </p>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li><strong>Access:</strong> Request a copy of all data we hold about you</li>
          <li><strong>Rectification:</strong> Correct inaccurate data</li>
          <li><strong>Erasure (Right to be Forgotten):</strong> Delete your account and all associated data via Settings → Delete Account</li>
          <li><strong>Portability:</strong> Export your session history and skill data</li>
          <li><strong>Objection:</strong> Opt out of any non-essential data processing</li>
        </ul>
        <p className="text-slate-600 dark:text-slate-400 mt-3">
          To exercise any of these rights, use the in-app controls in Settings, or email{" "}
          <a href="mailto:privacy@interviewcraft.ai" className="text-indigo-600 hover:underline">
            privacy@interviewcraft.ai
          </a>. We will respond within 30 days.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">6. Security</h2>
        <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
          <li>All data in transit is encrypted via TLS 1.2+</li>
          <li>Passwords are hashed with bcrypt (never stored in plain text)</li>
          <li>BYOK API keys are encrypted at rest with AES-256</li>
          <li>Audio never touches our servers — processed in real-time, then discarded</li>
          <li>Database access is restricted to application services only</li>
        </ul>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">7. Cookies</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          InterviewCraft stores your access token in memory only (never in localStorage or sessionStorage). A session cookie (<code>refresh_token</code>) is set as httpOnly and SameSite=Lax — JavaScript cannot read it. We do not use tracking cookies or third-party analytics scripts.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">8. Children&apos;s Privacy</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          The Service is not directed to children under 16. If you believe a child under 16 has created an account, contact us at{" "}
          <a href="mailto:privacy@interviewcraft.ai" className="text-indigo-600 hover:underline">
            privacy@interviewcraft.ai
          </a>{" "}
          and we will delete the account promptly.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">9. Changes to This Policy</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          We will notify you by email or in-app notice at least 14 days before material changes to this policy take effect.
        </p>

        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mt-8 mb-3">10. Contact</h2>
        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
          Data controller: InterviewCraft<br />
          Email:{" "}
          <a href="mailto:privacy@interviewcraft.ai" className="text-indigo-600 hover:underline">
            privacy@interviewcraft.ai
          </a>
        </p>

        <div className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-700 flex gap-4 text-sm">
          <Link href="/tos" className="text-indigo-600 hover:underline">Terms of Service</Link>
          <Link href="/" className="text-slate-400 hover:text-slate-600">← Back to home</Link>
        </div>
      </article>
    </main>
  );
}
