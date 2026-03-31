"""Admin metrics response schemas."""

from pydantic import BaseModel


class LatencyPercentiles(BaseModel):
    p50: float | None
    p95: float | None


class VoiceLatencyMetrics(BaseModel):
    stt: LatencyPercentiles
    llm_ttft: LatencyPercentiles
    tts: LatencyPercentiles
    e2e: LatencyPercentiles
    sample_count: int


class ScoringMetrics(BaseModel):
    avg_score: float | None
    score_stddev: float | None
    total_scored: int
    rewind_rate_pct: float  # % of segments that were rewound


class UsageMetrics(BaseModel):
    total_sessions: int
    completed_sessions: int
    completion_rate_pct: float
    total_cost_usd: float
    cost_per_session_usd: float
    cache_hit_rate_pct: float  # Anthropic prompt cache hit rate
    total_api_calls: int


class DailyLatencyPoint(BaseModel):
    date: str  # ISO date YYYY-MM-DD
    e2e_p50: float | None
    e2e_p95: float | None


class AdminMetricsResponse(BaseModel):
    # 7-day voice latency (DoD KPI: p95 < 1000ms)
    voice_7d: VoiceLatencyMetrics
    # 30-day scoring stats
    scoring_30d: ScoringMetrics
    # 30-day usage + cost
    usage_30d: UsageMetrics
    # Daily latency trend (last 14 days)
    latency_trend: list[DailyLatencyPoint]
    # Computed KPIs
    kpi_latency_ok: bool  # e2e p95 < 1000ms
    kpi_cache_ok: bool  # cache hit rate > 70%
    kpi_completion_ok: bool  # completion rate > 60%
