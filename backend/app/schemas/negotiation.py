"""Pydantic schemas for Negotiation Simulator."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class NegotiationStartRequest(BaseModel):
    """Body for POST /api/v1/negotiation/start."""

    company: str
    role: str
    level: str  # e.g. "L5", "Senior", "Staff"
    offer_amount: int  # their stated offer in USD
    market_rate: int  # candidate's target/market rate in USD
    quality_profile: str = "balanced"

    @field_validator("offer_amount", "market_rate")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class NegotiationStartResponse(BaseModel):
    """Response from POST /api/v1/negotiation/start — new session created."""

    session_id: uuid.UUID
    company: str
    role: str
    level: str
    offer_amount: int
    market_rate: int
    # Hidden from client — only shown in analysis
    # hidden_max computed server-side as offer * 1.15


class NegotiationScores(BaseModel):
    """Negotiation-specific score breakdown."""

    anchoring: int  # 0-100: did they anchor first and high?
    value_articulation: int  # 0-100: articulated their market value?
    counter_strategy: int  # 0-100: pushed back effectively?
    emotional_control: int  # 0-100: stayed calm, didn't concede under pressure?
    money_left_on_table: int  # estimated USD left unclaimed


class NegotiationRound(BaseModel):
    """One round of a negotiation session."""

    session_id: uuid.UUID
    round_number: int
    overall_score: int
    negotiation_scores: NegotiationScores
    final_offer: int | None  # what they accepted (if accepted)
    hidden_max: int  # what they could have gotten
    pattern_notes: list[str]  # patterns detected this round
    created_at: datetime


class NegotiationAnalysisResponse(BaseModel):
    """Full analysis for a negotiation session."""

    session_id: uuid.UUID
    company: str
    role: str
    level: str
    offer_amount: int
    market_rate: int
    hidden_max: int
    overall_score: int
    negotiation_scores: NegotiationScores
    pattern_detected: str | None  # cross-round pattern insight
    rounds_completed: int
    improvement_notes: list[str]


class NegotiationHistoryItem(BaseModel):
    """One item in negotiation history list."""

    session_id: uuid.UUID
    company: str
    role: str
    level: str
    offer_amount: int
    overall_score: int
    money_left_on_table: int
    created_at: datetime
    status: str  # active | completed | abandoned
