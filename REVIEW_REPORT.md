# Interviewcraft — final editorial and GitHub preparation review

Initial local-review snapshot: 6 November 2026, before commit/push/deployment. The subsequent security repair and GitHub release preparation are recorded at the end of this report.

## Public presentation

- Portfolio title remains **Voice AI Interview Coach — Independent Project**, with Alexander Doroshevich named as author. The strong implementation summary is unchanged.
- Removed internal audit language from the public case. The details now explain provider boundaries and how timestamp-linked quotes make feedback inspectable. No public Live demo link or invented adoption/result claim was added.
- README now follows purpose → engineering implementation → architecture → local setup → tests → one short limitations section. Review permissions, actions and historical results are recorded here rather than repeated in public project explanations.
- The demo screenshots remain explicitly labelled as static UI with hardcoded synthetic data. No recording of a real voice/AI session is claimed.

## Git reconciliation and preserved work

Fetched public main read-only. Local base `ad7f9c7a9a21613bdfd78e2be1d19fe14f337977` and public main `25149c7227576ed309d64aab82b97e69f2735796` have different commit histories but the **same tree**: `5cd746d110f9319496de5202fbf44e4f0e93bc28`. The divergence is four local commits versus two public commits, incorporating equivalent content.

Created local branch **codex/final-interviewcraft-review** at public main and carried the existing working changes onto it. No merge/cherry-pick or code rewrite was needed. Removed its automatic upstream association with origin/main; a future review-branch push must name the branch explicitly. Original branches remain available. All changes are still uncommitted.

The pre-existing user change in `frontend/package-lock.json` is preserved byte for byte (SHA256 `acf164d97daa32c5a9ae3620309350aaf19cdf4046fe981ce1eab979b89fe008`). It adds an optional Windows SWC package entry and is identified separately from the requested edits. No restoration or cleanup of that user change was performed.

Historical preservation exception, already disclosed in the previous review: Next regenerated the pre-existing modified `frontend/next-env.d.ts` before an exact original snapshot was obtained. It currently matches main; that earlier original delta cannot be reconstructed from the captured backup. This editorial pass did not modify it.

## Checks executed on this revision

| Check | Actual result |
|---|---|
| Backend offline suite | **419 passed, 40 integration/nightly deselected**, 3 deprecation warnings, 54.39s |
| Backend Ruff | Passed |
| Backend Mypy | Passed, 93 source files |
| Frontend Vitest | **9 passed**, 3 files |
| Portfolio tests | **45 passed** |
| Portfolio lint / TypeScript | Passed |
| Portfolio production build | Passed, Next.js 15.5.29, 10 generated pages; existing edge-runtime notice |
| Final Git diff whitespace check | Passed |
| README structure and local documentation links | Passed; no broken local links in the checked README/ADR/eval/benchmark pages |
| Base comparison / user lockfile | Identical base trees confirmed; user lockfile unchanged |
| Assistant source review | Seven requested topics grounded in final prompt/facts; no generated-answer pass claim |

Backend tests used the previously prepared isolated environment, fake credentials, disabled dotenv loading and a socket guard. They did not call real providers. Dependencies were reused; no fresh install is claimed in this pass. Backend code was not changed in this editorial pass. The independently accepted earlier frontend lint/type/build results remain historical; they were not repeated here because frontend source and dependencies were unchanged.

## Mobile capture

Replaced `docs/screenshots/local-demo-mobile.jpg` with a fresh capture of the actual local `/demo` route at a **390 × 844 CSS viewport**. The browser's returned JPEG is **385 × 832 pixels**; it was saved directly without resizing, cropping, padding or compositing. The top view is readable and vertical, without the old large empty field. A second bottom-of-page capture is included in the review bundle.

Checked the top navigation, cards, headings, lower content and final CTA. No horizontal overflow or elements extending beyond the viewport edges were observed. The synthetic skill table and cost values remain sample UI. No authentication, microphone or real-provider session was exercised.

## Assistant: current version and remaining evaluation

Updated project-specific instructions to explain the built work first. Memory, provider boundaries, scoring semantics, authorship, unknown current user counts and unverified public demo availability are handled under their respective questions, rather than appended to every introduction.

The review bundle contains `ASSISTANT_REVIEW.json`, the frozen `FINAL_PROMPT.txt`, seven questions and assessment criteria. Prompt SHA256: `288c85425830e8d4efab68d02e13d768aaf75350381beadb6def1461cecdcf84`. Public case, policy and model configuration hashes are also recorded. Configured model remains `claude-haiku-5-5`, 1200 output tokens, low effort; no model setting was changed here.

**Live evaluation was NOT RUN for this revision.** There is no new agreed paid-call budget. No actual answers, latency, model availability or quality ratings are claimed. Earlier evals belong to different prompt/fact snapshots and are not applied here. Seven source-grounding checks are not a substitute for reading generated answers. Full live voice → scoring → next-session memory, interruption on an actual device and real-provider fallback also remain unverified.

## Deployment and exact publication sequence

Existing workflow files were inspected and left unchanged:

- `.github/workflows/deploy.yml`: a push to main changing `backend/**` or `frontend/**` triggers backend checks and then Fly.io production deployment. It also supports manual dispatch; **dry_run defaults to false**. It is not an owner-approved release gate and does not wait for every separate frontend/PR check.
- Backend/frontend CI and PR Quality Gate have pull-request checks. Their comments do not prove branch-protection settings are enabled in GitHub.
- `.github/workflows/claude-review.yml`: opening/updating a PR to main can run a paid Claude review if the API secret is configured. Review or disable that automation before opening a PR if no review budget is approved.
- `frontend/vercel.json` exists. Hosting-account Git integrations, automatic previews and protections were not inspected; do not assume that a future branch push is deployment-free.

**Next action is owner review of the local diff and release automation.** Before any remote operation, confirm whether automatic Claude review and hosting previews are intended. Then, with separate commit/push approval, create signed DCO Conventional Commits for the scoped changes, push the named feature branch and open a PR to main. Keep the original user lockfile change identified separately. Watch all CI to completion. Before merge, make the existing production trigger and hosting Git integrations match the owner's publication decision. Do not merge while publication is still prohibited; the current deploy trigger can publish automatically. No permanent public AI backend is required for showcasing the source, architecture and screenshots.

Portfolio remains on its existing local branch with no remote configured. Its three editorial/test files are included separately in the review bundle; none of its unrelated pending changes were staged or attributed to this pass.


## Security remediation for PR #56

The first hosted quality gate found dependency-audit failures. These were repaired on the same PR without audit exclusions, ignored advisory IDs, weakened thresholds or new product features.

- Removed the unused Pipecat/NumPy dependency chain and the unused installed shadcn CLI; the custom asyncio voice runtime and existing UI components remain.
- Replaced python-jose/ecdsa with PyJWT, retaining the configured algorithm whitelist and the existing invalid-token response handling. Compatibility tests independently construct the previous compact HS256 format for access, refresh and password-reset tokens. Additional tests reject modified, unsigned, expired and wrong-algorithm tokens. See [PyJWT verification API](https://pyjwt.readthedocs.io/en/stable/api.html).
- Replaced PyPDF2 with its maintained successor pypdf, using the same PdfReader interface. A real synthetic single-page PDF exercises text extraction; malformed PDF still produces 422. See [pypdf project history](https://pypdf.readthedocs.io/en/stable/meta/history.html).
- Updated Next.js within version15 to15.5.29 and aligned eslint-config-next. Updated Vite/Vitest within a compatible Node20.19+ toolchain; React18 and Tailwind3 are unchanged. Targeted PostCSS/minimatch overrides fix pinned transitive dependencies. See [Vitest4 migration requirements](https://v4.vitest.dev/guide/migration.html).
- CI and Docker bootstrap pip26.3+; the frontend quality gate now uses npm ci with the committed lockfile. Dependency audits remain active.
- Kept the original user's optional Windows SWC lockfile entry in the working copy and saved the original bytes and patch locally. It is excluded from the committed clean lockfile.

Fresh local results: **428 backend tests passed,40 integration/nightly deselected,80.27% coverage**; Ruff and Mypy (93source files) passed. The nine added tests cover JWT/PDF compatibility and rejection. Frontend clean install, lint, TypeScript,9Vitest tests and production build passed. Ruff0.11.0, matching pre-commit, accepted all158backend files. Fresh pip-audit and npm audit both reported **0 known vulnerabilities**, including development dependencies. These are point-in-time audit results, not a guarantee against future advisories.

Hosted CI and deployment outcomes belong to the final commit's [PR checks](https://github.com/alexdoroshevich/Interviewcraft/pull/56/checks). Full live voice/scoring/next-session memory and updated portfolio-model response evaluation remain unverified; no paid provider calls were made during this security repair.
