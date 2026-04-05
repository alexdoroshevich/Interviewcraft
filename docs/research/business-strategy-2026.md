# InterviewCraft — Business Strategy Research 2026

Research conducted April 5, 2026. All sources cited inline. Critical and evidence-based.

---

## 1. Interview Duration Standards

### By Interview Type (per individual round)

| Interview Type | Real-World Duration | IC Default (min) | Notes |
|---|---|---|---|
| HR/Recruiter Screen | 15–30 min | 20 | Quick fit check |
| Behavioral | 30–45 min | 35 | Now 30–40% of FAANG interview time (up from 10–15% five years ago) |
| Technical/Coding | 45–60 min | 45 | Standard at FAANG; Meta does 2 problems in 35 min at senior level |
| System Design | 45–60 min | 50 | Sometimes 20 min at Amazon when mixed; default to full |
| Coding Discussion | 30–45 min | 35 | Code review / debugging; 2026 trend: reading existing code, not fresh puzzles |
| Negotiation | 15–30 min | 20 | Typically embedded in a broader call |
| Case Study (PM) | 30–45 min | 40 | |
| Case Study (DS) | 45–60 min | 50 | Data science cases run longer |
| Panel / Leadership | 45–90 min | 60 | Executive panels often multi-interviewer |
| Portfolio Review | 20–45 min | 30 | UX/Design: one main case study in depth |
| Diagnostic / Debrief | 20–30 min | 25 | IC-specific session types |

### By Profession

| Profession | Duration Tendency | Key Note |
|---|---|---|
| Software Engineer | Standard (45–60 min/round) | Use full defaults |
| Product Manager | Slightly shorter coding, longer behavioral (35–45 min) | Case study: 40 min default |
| Data Scientist | Long case studies (45–60 min) | Case study: 50 min default |
| Designer (UX/UI) | Portfolio 20–45 min, design challenge 45–60 min | Portfolio: 30 min default |
| Marketing | Mostly 30–45 min rounds | Reduce all defaults by 15% |
| Sales | Role plays 20–30 min, presentations 30–45 min | Negotiation: 25 min default |
| Finance | Modeling rounds 45–60 min | Use standard defaults |
| Operations | 30–45 min rounds | Reduce defaults by 10% |
| Leadership/Executive | 60–90 min/round, 4+ rounds over days | Panel: 60 min, allow override to 90 |

### By Company Tier

| Tier | Per-Round Duration | IC Adjustment |
|---|---|---|
| FAANG / Top-tier | 45–60 min | Use full defaults |
| Mid-size tech (Stripe, Uber, Airbnb) | 40–55 min | Reduce ~10% |
| Startup (Series A–C) | 30–60 min (variable) | Reduce ~15–20% |
| Non-tech enterprise | 30–45 min | Reduce ~20% |

### Recommended IC Session Defaults

| Session Type | Default (min) | Min | Max |
|---|---|---|---|
| `behavioral` | 35 | 15 | 60 |
| `system_design` | 50 | 20 | 75 |
| `coding_discussion` | 35 | 15 | 60 |
| `negotiation` | 20 | 10 | 45 |
| `diagnostic` | 25 | 10 | 40 |
| `debrief` | 25 | 10 | 40 |

---

## 2. AI Hiring Market — Size and Players (2026)

| Market Segment | Size (2026) | Growth |
|---|---|---|
| AI recruitment tools | ~$752M | 7.2% CAGR → $1.2B by 2033 |
| Mock interview services | $1.13B | 8.3% CAGR → $2.5B by 2035 |
| Interview prep tools (broader) | $2.5B | 11.8% CAGR → $6.3B by 2031 |
| AI coaching platforms | $4.22B | 11% CAGR → $12B by 2036 |
| Corporate training (total) | $102B/year | Stable |

### Key Competitors

| Company | Model | Weakness |
|---|---|---|
| **HireVue** | Enterprise video + AI scoring. 60% of Fortune 100. | Bias lawsuits (ACLU/Intuit, CVS class action). Dropped facial analysis. "Black box" reputation. |
| **Karat** | Live technical interviews with outsourced human interviewers | $200+/interview. Not AI-native. Supply-constrained. |
| **CodeSignal** | Automated coding assessments | No voice. Pure coding test, no behavioral or design. |
| **Final Round AI** | AI mock interviews, 10M+ users | Consumer-only. No B2B. Broad but shallow. |
| **Alex (YC, $17M)** | Voice AI for initial screening calls, thousands/day for Fortune 100 | Pure top-of-funnel screening. No prep, no coaching, no skill development. |
| **Paradox/Olivia** | Conversational AI recruiting (scheduling, chat screening) | Text-only chatbot. No voice assessment. |
| **Revarta** | AI behavioral interview prep, $49/month | Behavioral-only. No system design or coding. |
| **Interviewing.io** | Anonymous mock interviews with real engineers, $225+/session | Expensive. Human-constrained. Not scalable. |

---

## 3. HR Replacement: Viability Assessment

### What's actually viable today

| Capability | Viability | Evidence |
|---|---|---|
| AI initial screening calls | ✅ Proven | Alex doing thousands/day for Fortune 100. 88% of companies use AI screening somewhere. |
| Automated coding/technical assessment | ✅ Proven | CodeSignal, HackerRank. Table stakes. |
| AI scheduling and logistics | ✅ Proven | Paradox/Olivia. Low risk. |
| AI behavioral evaluation (structured rubrics) | ⚠️ Partial | Works for LP-driven formats (Amazon). "Culture fit" by AI remains controversial. |
| Internal skills coaching | ⚠️ Growing | Corporate coaching market buying. Long enterprise sales cycle. |
| Full replacement of human final-round interviewers | ❌ Not viable | No company has deployed this. Requires judgment, relationship-building, "selling the role" — AI cannot do this. |
| Multimodal body language / emotion analysis for hiring | ❌ Hype / illegal | EU AI Act bans emotion recognition in workplaces. HireVue dropped facial analysis after lawsuits. |
| AI-only hiring decisions | ❌ Not viable anywhere | No one is doing this. Every deployment keeps humans in the loop. |

### Legal and Regulatory Blockers

This is the single biggest obstacle. The regulatory environment in 2026 is actively hostile to AI hiring decisions:

**United States:**
- **New York City Local Law 144**: Annual independent bias audits required for any automated employment decision tool. Fines $500–$1,500/violation/day/affected applicant.
- **Illinois HB 3773** (effective Jan 1, 2026): Mandatory candidate notification when AI is used. Bans ZIP code as protected-class proxy.
- **Colorado AI Act** (effective June 30, 2026): Rigorous impact assessments required for "high-risk" AI in hiring/firing/promotion.

**European Union:**
- **EU AI Act** (high-risk enforcement August 2, 2026): Recruitment AI classified as high-risk. Requires bias testing, explainability, human oversight, logging, GDPR compliance.
- **Emotion recognition banned** in workplaces as of February 2, 2025.
- **Fines**: up to €35M or 7% of global revenue. Extraterritorial — applies to US companies affecting EU candidates.

**Bottom line**: Any B2B hiring product must have bias auditing, explainability, human oversight, and candidate notification built in from day one. This is not optional future work. This is enforceable law.

### Employer vs. Candidate Sentiment

- **Employers**: 87% of companies use AI-powered recruitment tools. 67% of TA professionals use AI somewhere in hiring. Employers are buying.
- **Candidates**: Significant backlash. ACLU filed ADA discrimination complaint against Intuit's HireVue use. CVS settled a class action. Non-native English speakers and disabled individuals score systematically lower. Candidates game the system rather than present authentically.
- **The gap**: Employers want efficiency. Candidates want fairness. A product that serves both sides has a structural advantage.

---

## 4. Strategic Recommendation: B2B Path

### Do NOT pursue screening replacement in year 1

The compliance burden (SOC 2, bias auditing, legal review, enterprise procurement) is too heavy for a small team. The risk/reward is wrong.

### DO pursue B2B via the Training door

**Why training beats screening:**
- Internal training ≠ adverse employment action → lower regulatory burden
- Employees *want* to use the product → brand trust maintained
- Shorter sales cycle ($20–50/user/month vs. $50K–$200K platform license)
- We are trusted by candidates. HireVue is feared. That is our competitive advantage.

### B2B Minimum Viable Feature Set

1. Team/org account management (admin dashboard, user provisioning)
2. Custom interview flow configuration (rubrics, question banks, company context)
3. Team-level analytics and reporting (aggregate skill maps, progress over time)
4. SSO (SAML/OIDC — non-negotiable for enterprise)
5. Data export / API for HR systems
6. SOC 2 Type II (required for contracts over $50K)

### Revenue Projections (Conservative)

| Timeline | Revenue Range | Driver |
|---|---|---|
| Month 6 | $10K–$30K MRR | B2C subscriptions (1K–3K paying users) |
| Month 12 | $30K–$80K MRR | B2C + 5–10 B2B training pilots |
| Month 18 | $80K–$200K MRR | B2B training gaining traction |

---

## 5. Top 5 Differentiating Features

Ranked by impact × feasibility × defensibility.

### 1. Evidence-Linked Real-Time Coaching (Impact: 10, Feasibility: 8, Defensibility: 9)

After each answer, before the next question, show quote-level highlights from the transcript (using existing `transcript_words` timestamps) identifying exactly what was strong/weak and why, with specific rewrite suggestions. Not post-session — turn-by-turn.

**Why it wins**: No competitor does this at the evidence level. Final Round AI and Huru.ai give tone/pacing feedback, but none link feedback to specific transcript quotes with timestamp evidence. InterviewCraft already has the infrastructure.

**Effort**: 2–3 weeks. New coaching mode flag, interstitial coaching card component, Haiku scoring per turn (~$0.01/analysis). Fully compatible with existing stack.

### 2. Anonymized Peer Benchmarking (Impact: 9, Feasibility: 7, Defensibility: 8)

After each session: "Your behavioral score for Amazon was 72 — 68th percentile of candidates practicing Amazon behavioral interviews." Skill-level percentiles, not just overall score.

**Why it wins**: Network effect — more users = better benchmarks. No competitor has this for voice-based behavioral and system design sessions. Interviewing.io has some coding benchmarks only.

**Effort**: 3–4 weeks. Aggregate anonymized scoring data. Percentile calculation batch job. Privacy: only show percentiles when cohort size > 50. Redis cache for common percentile queries.

### 3. JD-Driven Adaptive Sessions (Impact: 8, Feasibility: 9, Defensibility: 7)

JD analyzer already exists (`POST /api/v1/sessions/analyze-jd`). Gap: the JD analysis doesn't currently drive the actual interview questions or interviewer behavior in real-time.

**Why it wins**: Feed JD analysis output into system prompt as a focus directive. Interviewer probes specifically on JD-mentioned skills. Scoring rubric becomes JD-relevant.

**Effort**: 1–2 weeks. Extends existing infrastructure. Highest ROI/effort ratio on this list.

### 4. Interview Calendar + Countdown Prep Plan (Impact: 7, Feasibility: 8, Defensibility: 6)

Google Calendar / Outlook integration. When an interview is scheduled, generate: "5 days until Amazon System Design. Based on your skill graph, focus on: distributed systems (score 58, below benchmark). Recommended: 2 system design sessions."

**Why it wins**: No mock interview platform ties into the candidate's actual interview schedule. Transforms InterviewCraft from optional practice into a countdown-driven prep partner. Creates stickiness and daily active usage.

**Effort**: 3–4 weeks. Google Calendar API + Microsoft Graph API. Event detection heuristic. Prep plan generator (Haiku). Frontend countdown widget.

### 5. Company Intel Layer — Living Knowledge Base (Impact: 7, Feasibility: 6, Defensibility: 7)

Beyond the 12 existing company playbooks: community-contributed interview intelligence. Users report what they saw in their real interview. Anonymized and aggregated into AI-driven insight: "Based on 47 recent reports, Google is now asking more AI/ML integration questions in system design. Let's practice that."

**Why it wins**: Levels.fyi and Glassdoor have static question databases. InterviewCraft can turn community intelligence into adaptive AI sessions.

**Effort**: 6–8 weeks (hardest feature: user contribution mechanics, moderation, anonymization). New tables, new moderation workflow, ChromaDB integration.

### Features Explicitly Rejected

| Feature | Why Not |
|---|---|
| Video / body language / emotion analysis | EU AI Act bans emotion recognition in workplaces. HireVue dropped facial analysis after lawsuits. Legally radioactive. |
| Real-time interview assistance (cheat during actual interview) | Destroys brand integrity and any future B2B credibility. Let competitors own that reputation. |
| AI avatar video interviews | Uncanny valley persists. Voice-only is more natural for practice and avoids regulatory minefield. |
| AI-only hiring decisions | No viable market. Every deployment keeps humans in the loop. |

---

## 6. 12-Month Strategic Roadmap

### Phase 1: Cement B2C Dominance (Months 1–3)

| Feature | Effort | Impact |
|---|---|---|
| Session duration defaults (this research) | 1 week | Professional standard |
| Evidence-linked real-time coaching | 2–3 weeks | Killer differentiator |
| JD-driven adaptive sessions (extend existing) | 1–2 weeks | High ROI, low effort |
| Anonymized peer benchmarking (backend pipeline first) | 3–4 weeks | Network effect |

### Phase 2: Prepare for B2B (Months 3–6)

| Feature | Effort |
|---|---|
| Calendar integration + countdown prep plans | 3–4 weeks |
| Team accounts (admin, user provisioning) | 4–6 weeks |
| Custom interview flow configuration | 3–4 weeks |
| Begin SOC 2 Type I process | $50K–$100K, 3–6 months |

### Phase 3: Launch B2B Training Product (Months 6–9)

| Feature | Effort |
|---|---|
| Team analytics dashboard | 3–4 weeks |
| SSO (SAML + OIDC) | 2–3 weeks |
| Data export API | 1–2 weeks |
| Land first 5 pilot customers (200–2,000 employee tech companies) | Ongoing |

### Phase 4: Expand (Months 9–12)

| Feature | Effort |
|---|---|
| Company intel layer (community contributions) | 6–8 weeks |
| SOC 2 Type II certification | Calendar-bound |
| Assessment reporting (export to HR systems) | 2–3 weeks |
| Bias audit framework (if pursuing screening use case) | 4–6 weeks |

---

## Sources

- AI Recruitment Market: DemandSage, SkyQuest (2026)
- Coaching Platform Market: Future Market Insights, Market.us (2026)
- EU AI Act HR implications: Crowell & Moring, HeroHunt, Fisher Phillips (2026)
- US AI hiring laws: Akerman LLP, Holland & Knight, Fisher Phillips (2026)
- HireVue bias cases: SHRM, HR Dive (2024–2025)
- Alex (AI recruiter) $17M Series A: TechBuzz (2026)
- Interview format norms: Interviewing.io, Exponent, Design Gurus, AIHR (2025–2026)
- Mock interview market: WiseGuy Reports, Verified Market Research (2025–2026)
- Corporate training spend: Training Orchestra, Josh Bersin (2026)
- SOC 2 for AI companies: Comp AI, SecureSlate (2026)
