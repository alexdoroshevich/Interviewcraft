/**
 * Typed API client — wraps fetch with auth headers.
 *
 * Token strategy (2026):
 *   - Access token lives in module-level memory only — never written to
 *     localStorage or sessionStorage.  XSS cannot exfiltrate it across page
 *     loads because the variable resets on every navigation.
 *   - Refresh token lives in an httpOnly, SameSite=Lax cookie set by the
 *     backend.  JS cannot read it at all.
 *   - On page load useAuth calls tryRefreshToken() which hits POST /auth/refresh
 *     (the backend reads the cookie automatically); on success the new access
 *     token is stored in _accessToken and the page renders.
 *   - On 401 during any API call, apiFetch auto-refreshes once via the same
 *     mechanism before giving up and redirecting to /login.
 */

const PROD_API_URL = "https://interviewcraft-api.fly.dev";
const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? PROD_API_URL)
    : PROD_API_URL;

// In-memory access token — intentionally not persisted anywhere.
let _accessToken: string | null = null;

export function setToken(token: string): void {
  _accessToken = token;
}

export function clearToken(): void {
  _accessToken = null;
}

export function getToken(): string | null {
  return _accessToken;
}

/**
 * Attempt a silent token refresh using the httpOnly refresh cookie.
 * Call this once on app startup (useAuth hook).
 * Returns the new access token on success, null on failure.
 */
export async function tryRefreshToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return null;
    const { access_token } = await res.json() as { access_token: string };
    setToken(access_token);
    return access_token;
  } catch {
    return null;
  }
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });

  // Auto-refresh expired access token using httpOnly refresh cookie
  if (res.status === 401 && path !== "/api/v1/auth/refresh") {
    const refreshRes = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (refreshRes.ok) {
      const { access_token } = await refreshRes.json() as { access_token: string };
      setToken(access_token);
      const retryRes = await fetch(`${API_BASE}${path}`, {
        ...init,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${access_token}`,
          ...(init.headers ?? {}),
        },
      });
      if (!retryRes.ok) {
        let msg = `HTTP ${retryRes.status}`;
        try { msg = (await retryRes.json()).detail ?? msg; } catch { /* no-op */ }
        throw new ApiError(retryRes.status, msg);
      }
      if (retryRes.status === 204) return undefined as unknown as T;
      return retryRes.json();
    } else {
      clearToken();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "Session expired. Please sign in again.");
    }
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch { /* no-op */ }
    throw new ApiError(res.status, msg);
  }

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface SessionResponse {
  id: string;
  type: string;
  interview_type: string | null;
  status: string;
  quality_profile: string;
  voice_id: string | null;
  persona: string;
  company: string | null;
  focus_skill: string | null;
  duration_limit_minutes: number | null;
  total_cost_usd: string;
  created_at: string;
  ended_at: string | null;
}

export interface TranscriptTurn {
  role: "user" | "assistant";
  content: string;
  ts_ms: number;
}

export interface SessionDetail extends SessionResponse {
  transcript: TranscriptTurn[];
  lint_results: Record<string, unknown> | null;
}

export interface JdFocusArea {
  area: string;
  reason: string;
  priority: "high" | "medium" | "low";
}

export interface JdAnalysisResponse {
  skills_required: string[];
  skills_nice_to_have: string[];
  seniority: string;
  role_type: string;
  suggested_session_type: string;
  suggested_company: string | null;
  focus_areas: JdFocusArea[];
  coaching_note: string;
  input_tokens: number;
  output_tokens: number;
}

export interface EvidenceSpan {
  start_ms: number;
  end_ms: number;
  server_extracted_quote: string | null;
}

export interface RuleTriggered {
  rule: string;
  confidence: "strong" | "weak";
  evidence: EvidenceSpan;
  fix: string;
  impact: string;
}

export interface DiffChange {
  before: string;
  after: string;
  rule: string;
  impact: string;
}

export interface DiffVersion {
  text: string;
  changes: DiffChange[];
  estimated_new_score: number;
}

export interface DiffVersions {
  minimal: DiffVersion;
  medium: DiffVersion;
  ideal: DiffVersion;
}

export interface LevelAssessment {
  l4: "pass" | "borderline" | "fail";
  l5: "pass" | "borderline" | "fail";
  l6: "pass" | "borderline" | "fail";
  gaps: string[];
}

export interface SegmentScoreResponse {
  id: string;
  session_id: string;
  segment_index: number;
  question_text: string;
  answer_text: string;
  overall_score: number;
  confidence: string;
  category_scores: Record<string, number>;
  rules_triggered: RuleTriggered[];
  level_assessment: LevelAssessment;
  diff_versions: DiffVersions | null;
  rewind_count: number;
  best_rewind_score: number | null;
  created_at: string;
}

export interface ScoringStatusResponse {
  session_id: string;
  segments_scored: number;
  total_cost_usd: number;
  cache_hit_tokens: number;
  scores: SegmentScoreResponse[];
}

// ── Delivery analysis ──────────────────────────────────────────────────────────

export interface DeliveryAnalysisResponse {
  total_words: number;
  duration_seconds: number;
  wpm: number;
  filler_count: number;
  filler_rate: number;
  fillers_by_type: Record<string, number>;
  top_filler: string | null;
  hesitation_gaps: Array<{ start_ms: number; end_ms: number; duration_ms: number }>;
  long_pause_count: number;
  has_word_timestamps: boolean;
  delivery_score: number;
  delivery_grade: string;
  coaching_tips: string[];
}

// ── Skill graph ────────────────────────────────────────────────────────────────

export interface SkillNodeResponse {
  id: string;
  skill_name: string;
  skill_category: string;
  current_score: number;
  best_score: number;
  trend: "improving" | "declining" | "stable";
  last_practiced: string | null;
  next_review_due: string | null;
  evidence_links: Record<string, unknown>[];
  typical_mistakes: string[];
  created_at: string;
  updated_at: string;
}

export interface SkillGraphResponse {
  user_id: string;
  total_skills: number;
  nodes: SkillNodeResponse[];
  avg_score: number;
  weakest_category: string | null;
  strongest_category: string | null;
}

export interface DrillSlot {
  day: string;
  skill_name: string;
  skill_category: string;
  current_score: number;
  trend: string;
  questions: number;
  estimated_minutes: number;
  focus_note: string;
}

export interface DrillPlanResponse {
  slots: DrillSlot[];
  total_skills: number;
  weakest_skill: string | null;
  estimated_minutes_per_week: number;
  generated_at: string;
  message: string | null;
  days_until_interview: number | null;
  interview_urgency: string | null;
}

export interface BeatYourBestItem {
  skill_name: string;
  skill_category: string;
  current_score: number;
  best_score: number;
  gap: number;
  can_beat: boolean;
}

export interface BenchmarkResponse {
  overall_percentile: number;
  by_category: Record<string, number>;
  your_avg_score: number;
  platform_avg_score: number;
  sample_size: number;
}

export interface SkillHistoryPoint {
  date: string;
  score: number;
  session_id: string | null;
}

export interface SkillHistoryResponse {
  skill_name: string;
  current_score: number;
  best_score: number;
  trend: string;
  history: SkillHistoryPoint[];
}

// ── Rewind ─────────────────────────────────────────────────────────────────────

export interface RewindStartResponse {
  segment_id: string;
  question: string;
  original_score: number;
  original_answer_text: string;
  hint: string;
  rules_to_fix: string[];
}

export interface CategoryDelta {
  structure: number;
  depth: number;
  communication: number;
  seniority_signal: number;
}

export interface RewindScoreResponse {
  segment_id: string;
  original_score: number;
  new_score: number;
  delta: number;
  categories_delta: CategoryDelta;
  rules_fixed: string[];
  rules_new: string[];
  reason: string;
  rewind_count: number;
  best_rewind_score: number;
}

export interface QuestionResponse {
  id: string;
  text: string;
  type: string;
  difficulty: string;
  skills_tested: string[];
  company?: string | null;
  status?: string;
  upvotes?: number;
  submitted_by?: string | null;
}

export interface ContributeQuestionRequest {
  text: string;
  type: string;
  difficulty: string;
  skills_tested: string[];
  company?: string | null;
}

export interface ContributeQuestionResponse {
  id: string;
  status: string;
  message: string;
}

// ── Stories ────────────────────────────────────────────────────────────────────

export interface StoryResponse {
  id: string;
  user_id: string;
  title: string;
  summary: string;
  competencies: string[];
  times_used: number;
  last_used: string | null;
  best_score_with_this_story: number | null;
  warnings: string[];
  source_session_id: string | null;
  auto_detected: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoryCreateRequest {
  title: string;
  summary: string;
  competencies: string[];
  source_session_id?: string;
  auto_detected?: boolean;
}

export interface CompetencyCoverage {
  competency: string;
  status: "strong" | "weak" | "gap";
  story_count: number;
  stories: { id: string; title: string; times_used: number; best_score: number | null }[];
  action: string | null;
}

export interface CoverageMapResponse {
  competencies: CompetencyCoverage[];
  total_stories: number;
  covered: number;
  gaps: number;
  coverage_pct: number;
}

// ── Negotiation ────────────────────────────────────────────────────────────────

export interface NegotiationStartRequest {
  company: string;
  role: string;
  level: string;
  offer_amount: number;
  market_rate: number;
  quality_profile?: string;
}

export interface NegotiationStartResponse {
  session_id: string;
  company: string;
  role: string;
  level: string;
  offer_amount: number;
  market_rate: number;
}

export interface NegotiationScores {
  anchoring: number;
  value_articulation: number;
  counter_strategy: number;
  emotional_control: number;
  money_left_on_table: number;
}

export interface NegotiationHistoryItem {
  session_id: string;
  company: string;
  role: string;
  level: string;
  offer_amount: number;
  overall_score: number;
  money_left_on_table: number;
  created_at: string;
  status: string;
}

export interface NegotiationAnalysisResponse {
  session_id: string;
  company: string;
  role: string;
  level: string;
  offer_amount: number;
  market_rate: number;
  hidden_max: number;
  overall_score: number;
  negotiation_scores: NegotiationScores;
  pattern_detected: string | null;
  rounds_completed: number;
  improvement_notes: string[];
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface RecentSession {
  id: string;
  type: string;
  status: string;
  created_at: string;
  avg_score: number | null;
  cost_usd: number;
}

export interface SessionMetricsResponse {
  turns: number;
  e2e_p50_ms: number | null;
  e2e_p95_ms: number | null;
  e2e_avg_ms: number | null;
  stt_avg_ms: number | null;
  llm_avg_ms: number | null;
  tts_avg_ms: number | null;
}

export interface DashboardResponse {
  total_sessions: number;
  sessions_last_30_days: number;
  sessions_scored: number;
  avg_score_all_time: number | null;
  avg_score_last_30_days: number | null;
  best_session_score: number | null;
  total_skills_tracked: number;
  avg_skill_score: number | null;
  weakest_skill: string | null;
  strongest_skill: string | null;
  total_stories: number;
  coverage_pct: number;
  total_negotiation_sessions: number;
  avg_negotiation_score: number | null;
  avg_money_left_on_table: number | null;
  total_cost_usd: number;
  cost_last_30_days: number;
  readiness_estimate: number | null;
  recent_sessions: RecentSession[];
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── Profile / Self-Assessment ─────────────────────────────────────────────────

export interface SelfAssessmentRequest {
  target_company: string;
  target_level: string;
  weak_areas: string[];
  interview_timeline: string;
}

export interface SelfAssessmentResponse {
  target_company: string;
  target_level: string;
  weak_areas: string[];
  interview_timeline: string;
  completed_at: string;
}

export interface SelfAssessmentStatus {
  completed: boolean;
  data: SelfAssessmentResponse | null;
}

export interface InterviewDateResponse {
  interview_date: string | null;  // ISO date YYYY-MM-DD
  days_until: number | null;
}

// ── Resume / Profile types ─────────────────────────────────────────────────

export interface ProjectItem {
  title: string;
  description: string;
  impact: string;
}

export interface ResumeProfile {
  experience_years: number | null;
  current_role: string | null;
  target_role: string | null;
  target_level: string | null;
  target_company: string | null;
  skills: string[];
  projects: ProjectItem[];
  experience_summary: string | null;
}

export interface ResumeUploadResponse {
  message: string;
  profile: ResumeProfile;
}

// ── Settings / BYOK ────────────────────────────────────────────────────────────

export interface SettingsResponse {
  default_quality_profile: string;
  email_digest: boolean;
  openai_model: string;
  byok_providers: string[];
  byok_key_previews: Record<string, string>;
}

export interface ByokUpdateRequest {
  anthropic?: string;
  openai?: string;
  deepgram?: string;
  elevenlabs?: string;
}

export interface ResumeProfileResponse {
  profile: ResumeProfile | null;
  has_resume: boolean;
}

/**
 * Upload a file via multipart/form-data.
 * Does NOT set Content-Type — the browser sets it with the boundary.
 */
async function apiUpload<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const token = getToken();

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch { /* no-op */ }
    throw new ApiError(res.status, msg);
  }

  return res.json();
}

// ── API surface ────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    register: (email: string, password: string) =>
      apiFetch<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    login: (email: string, password: string) =>
      apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    googleLogin: (idToken: string) =>
      apiFetch<TokenResponse>("/api/v1/auth/google", {
        method: "POST",
        body: JSON.stringify({ id_token: idToken }),
      }),

    me: () => apiFetch<UserResponse>("/api/v1/auth/me"),
  },

  sessions: {
    list: (limit = 20, offset = 0) =>
      apiFetch<SessionResponse[]>(`/api/v1/sessions?limit=${limit}&offset=${offset}`),

    get: (id: string) => apiFetch<SessionDetail>(`/api/v1/sessions/${id}`),

    create: (type: string, quality_profile = "balanced", interview_type?: string, voice_id?: string, persona = "neutral", company: string | null = null, focus_skill?: string, duration_limit_minutes?: number) =>
      apiFetch<SessionResponse>("/api/v1/sessions", {
        method: "POST",
        body: JSON.stringify({ type, quality_profile, interview_type, voice_id, persona, company, focus_skill, duration_limit_minutes }),
      }),

    end: (id: string, status: "completed" | "abandoned" = "completed") =>
      apiFetch<SessionResponse>(`/api/v1/sessions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),

    delete: (id: string) =>
      apiFetch<void>(`/api/v1/sessions/${id}`, { method: "DELETE" }),

    metrics: (id: string) =>
      apiFetch<SessionMetricsResponse>(`/api/v1/sessions/${id}/metrics`),

    analyzeJd: (jd_text: string) =>
      apiFetch<JdAnalysisResponse>("/api/v1/sessions/analyze-jd", {
        method: "POST",
        body: JSON.stringify({ jd_text }),
      }),

    downloadReport: async (id: string): Promise<void> => {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${id}/report`, {
        credentials: "include",
        headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "Download failed");
        throw new ApiError(res.status, text);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `coaching-report-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    },
  },

  scoring: {
    score: (sessionId: string, forceRescore = false) =>
      apiFetch<ScoringStatusResponse>(`/api/v1/sessions/${sessionId}/score`, {
        method: "POST",
        body: JSON.stringify({ force_rescore: forceRescore }),
      }),

    getScores: (sessionId: string) =>
      apiFetch<SegmentScoreResponse[]>(`/api/v1/sessions/${sessionId}/scores`),

    getDelivery: (sessionId: string) =>
      apiFetch<DeliveryAnalysisResponse>(`/api/v1/sessions/${sessionId}/delivery`),
  },

  rewind: {
    start: (sessionId: string, segmentId: string) =>
      apiFetch<RewindStartResponse>(`/api/v1/sessions/${sessionId}/rewind`, {
        method: "POST",
        body: JSON.stringify({ segment_id: segmentId }),
      }),

    score: (sessionId: string, segmentId: string, answerText: string) =>
      apiFetch<RewindScoreResponse>(
        `/api/v1/sessions/${sessionId}/rewind/${segmentId}/score`,
        {
          method: "POST",
          body: JSON.stringify({ answer_text: answerText }),
        }
      ),
  },

  skills: {
    getGraph: () => apiFetch<SkillGraphResponse>("/api/v1/skills"),
    getPlan: () => apiFetch<DrillPlanResponse>("/api/v1/skills/plan"),
    getHistory: () => apiFetch<SkillHistoryResponse[]>("/api/v1/skills/history"),
    getBest: () => apiFetch<BeatYourBestItem[]>("/api/v1/skills/best"),
    getBenchmark: () => apiFetch<BenchmarkResponse>("/api/v1/skills/benchmark"),
  },

  questions: {
    next: (skill?: string, type?: string) => {
      const params = new URLSearchParams();
      if (skill) params.set("skill", skill);
      if (type) params.set("type", type);
      const qs = params.toString();
      return apiFetch<QuestionResponse>(`/api/v1/questions/next${qs ? `?${qs}` : ""}`);
    },

    contribute: (body: ContributeQuestionRequest) =>
      apiFetch<ContributeQuestionResponse>("/api/v1/questions/contribute", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    myContributions: () =>
      apiFetch<QuestionResponse[]>("/api/v1/questions/contribute"),

    upvote: (questionId: string) =>
      apiFetch<void>(`/api/v1/questions/${questionId}/upvote`, { method: "POST" }),
  },

  stories: {
    list: () => apiFetch<StoryResponse[]>("/api/v1/stories"),
    create: (body: StoryCreateRequest) =>
      apiFetch<StoryResponse>("/api/v1/stories", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: Partial<StoryCreateRequest>) =>
      apiFetch<StoryResponse>(`/api/v1/stories/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete: (id: string) =>
      apiFetch<void>(`/api/v1/stories/${id}`, { method: "DELETE" }),
    coverage: () => apiFetch<CoverageMapResponse>("/api/v1/stories/coverage"),
  },

  negotiation: {
    start: (body: NegotiationStartRequest) =>
      apiFetch<NegotiationStartResponse>("/api/v1/negotiation/start", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    history: () => apiFetch<NegotiationHistoryItem[]>("/api/v1/negotiation/history"),
    analysis: (sessionId: string) =>
      apiFetch<NegotiationAnalysisResponse>(`/api/v1/negotiation/${sessionId}/analysis`),
  },

  dashboard: {
    get: () => apiFetch<DashboardResponse>("/api/v1/dashboard"),
  },

  admin: {
    metrics: () => apiFetch<AdminMetricsResponse>("/api/v1/admin/metrics"),
  },

  profile: {
    getSelfAssessment: () =>
      apiFetch<SelfAssessmentStatus>("/api/v1/profile/self-assessment"),
    saveSelfAssessment: (data: SelfAssessmentRequest) =>
      apiFetch<SelfAssessmentResponse>("/api/v1/profile/self-assessment", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getInterviewDate: () =>
      apiFetch<InterviewDateResponse>("/api/v1/profile/interview-date"),
    setInterviewDate: (date: string | null) =>
      apiFetch<InterviewDateResponse>("/api/v1/profile/interview-date", {
        method: "PATCH",
        body: JSON.stringify({ interview_date: date }),
      }),
  },

  resume: {
    upload: (file: File) =>
      apiUpload<ResumeUploadResponse>("/api/v1/resume/upload", file),
    getProfile: () =>
      apiFetch<ResumeProfileResponse>("/api/v1/resume/profile"),
    updateProfile: (data: Partial<ResumeProfile>) =>
      apiFetch<ResumeProfileResponse>("/api/v1/resume/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  settings: {
    get: () => apiFetch<SettingsResponse>("/api/v1/settings"),
    patch: (data: { default_quality_profile?: string; email_digest?: boolean; openai_model?: string }) =>
      apiFetch<SettingsResponse>("/api/v1/settings", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    upsertByok: (keys: ByokUpdateRequest) =>
      apiFetch<SettingsResponse>("/api/v1/settings/byok", {
        method: "POST",
        body: JSON.stringify(keys),
      }),
    deleteByok: () =>
      apiFetch<SettingsResponse>("/api/v1/settings/byok", { method: "DELETE" }),
    testByok: (provider: string, key: string) =>
      apiFetch<{ ok: boolean; message: string }>("/api/v1/settings/byok/test", {
        method: "POST",
        body: JSON.stringify({ provider, key }),
      }),
    deleteAccount: () =>
      apiFetch<void>("/api/v1/settings/account", { method: "DELETE" }),
  },

  share: {
    createCard: () =>
      apiFetch<ShareCardCreateResponse>("/api/v1/share/card", { method: "POST" }),

    getCard: (token: string) =>
      apiFetch<ShareCardPublicResponse>(`/api/v1/share/card/${token}`),
  },

  companies: {
    getIntel: (company: string) =>
      apiFetch<CompanyIntelListResponse>(`/api/v1/companies/${encodeURIComponent(company)}/intel`),
    submitIntel: (company: string, category: string, content: string) =>
      apiFetch<CompanyIntelItem>(`/api/v1/companies/${encodeURIComponent(company)}/intel`, {
        method: "POST",
        body: JSON.stringify({ category, content }),
      }),
    upvote: (company: string, intelId: string) =>
      apiFetch<{ upvotes: number }>(`/api/v1/companies/${encodeURIComponent(company)}/intel/${intelId}/upvote`, {
        method: "POST",
      }),
  },
};

export { ApiError };

// ── Company Intel ──────────────────────────────────────────────────────────────

export interface CompanyIntelItem {
  id: string;
  company: string;
  category: string;
  content: string;
  upvotes: number;
  created_at: string;
}

export interface CompanyIntelListResponse {
  company: string;
  items: CompanyIntelItem[];
  total: number;
}

// ── Share card ─────────────────────────────────────────────────────────────────

export interface ShareCardSnapshot {
  readiness_score: number;
  avg_skill_score: number;
  skill_scores_by_category: Record<string, number>;
  top_strengths: string[];
  session_count: number;
  generated_at: string;
}

export interface ShareCardCreateResponse {
  token: string;
  share_url: string;
  expires_at: string | null;
}

export interface ShareCardPublicResponse {
  token: string;
  snapshot: ShareCardSnapshot;
  created_at: string;
  expires_at: string | null;
}

// ── Admin types ────────────────────────────────────────────────────────────────

export interface LatencyPercentiles { p50: number | null; p95: number | null }
export interface VoiceLatencyMetrics {
  stt: LatencyPercentiles; llm_ttft: LatencyPercentiles;
  tts: LatencyPercentiles; e2e: LatencyPercentiles; sample_count: number;
}
export interface ScoringMetrics {
  avg_score: number | null; score_stddev: number | null;
  total_scored: number; rewind_rate_pct: number;
}
export interface UsageMetrics {
  total_sessions: number; completed_sessions: number;
  completion_rate_pct: number; total_cost_usd: number;
  cost_per_session_usd: number; cache_hit_rate_pct: number; total_api_calls: number;
}
export interface DailyLatencyPoint { date: string; e2e_p50: number | null; e2e_p95: number | null }
export interface AdminMetricsResponse {
  voice_7d: VoiceLatencyMetrics; scoring_30d: ScoringMetrics;
  usage_30d: UsageMetrics; latency_trend: DailyLatencyPoint[];
  kpi_latency_ok: boolean; kpi_cache_ok: boolean; kpi_completion_ok: boolean;
}
