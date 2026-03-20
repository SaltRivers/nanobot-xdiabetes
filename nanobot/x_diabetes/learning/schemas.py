"""Schemas for X-Diabetes continuous learning.

The learning pipeline intentionally stores only sanitized workflow metadata so
that repeated usage patterns can be turned into draft skills without persisting
patient-specific content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from nanobot.x_diabetes.schemas import FlexibleModel

LearningVerdict = Literal["drop", "revise", "review", "approve", "activate"]
LearningDraftStatus = Literal[
    "draft",
    "approved",
    "rejected",
    "activated",
    "deactivated",
    "rolled_back",
]


class LearningObservation(FlexibleModel):
    """Sanitized observation captured from one agent turn."""

    observation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_key: str
    mode: Literal["doctor", "patient"] = "doctor"
    domain: str = "workflow"
    task: str = "general"
    tool_names: list[str] = Field(default_factory=list)
    tool_sequence_signature: str = ""
    intent_labels: list[str] = Field(default_factory=list)
    message_features: list[str] = Field(default_factory=list)
    pattern_key: str
    report_requested: bool = False
    safety_tool_used: bool = False
    error_count: int = 0
    correction_signal: bool = False
    redaction_count: int = 0
    blocked_reasons: list[str] = Field(default_factory=list)


class LearningInstinct(FlexibleModel):
    """Atomic reusable pattern distilled from repeated observations."""

    instinct_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str
    trigger: str
    action: str
    rationale: str = ""
    domain: str = "workflow"
    mode: Literal["doctor", "patient"] = "doctor"
    task: str = "general"
    pattern_key: str
    confidence: float = 0.0
    evidence_count: int = 0
    evidence_observation_ids: list[str] = Field(default_factory=list)
    correction_rate: float = 0.0
    error_rate: float = 0.0
    report_requested: bool = False
    safety_tool_used: bool = False
    status: Literal["tentative", "strong"] = "tentative"


class LearningSkillDraft(FlexibleModel):
    """Draft skill generated from one or more strong instincts."""

    draft_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    skill_name: str
    title: str
    description: str
    domain: str = "workflow"
    mode: Literal["doctor", "patient"] = "doctor"
    task: str = "general"
    trigger_summary: str
    workflow_summary: str
    source_instinct_ids: list[str] = Field(default_factory=list)
    source_observation_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    status: LearningDraftStatus = "draft"
    skill_markdown: str
    activation_notes: list[str] = Field(default_factory=list)


class LearningEvaluationResult(FlexibleModel):
    """Result of evaluating an instinct, draft, or activation candidate."""

    evaluation_id: str
    entity_type: Literal["instinct", "draft", "activation"]
    entity_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checklist: dict[str, bool] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    verdict: LearningVerdict = "review"
    rationale: str = ""
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    synthetic_cases_passed: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningPolicy(FlexibleModel):
    """Workspace-local learning policy loaded from JSON."""

    blocked_regexes: list[str] = Field(default_factory=list)
    blocked_field_names: list[str] = Field(default_factory=list)
    required_skill_sections: list[str] = Field(default_factory=list)
    safety_keywords: list[str] = Field(default_factory=list)
    synthetic_eval_cases: list[dict[str, Any]] = Field(default_factory=list)
    min_observations_to_learn: int = 3
    min_confidence_to_draft: float = 0.7
    max_similarity_before_conflict: float = 0.82


class ActivatedSkillState(FlexibleModel):
    """Monitoring state for one activated learned skill."""

    skill_name: str
    draft_id: str
    activated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["active", "needs_review", "deactivated", "rolled_back"] = "active"
    usage_count: int = 0
    contradiction_count: int = 0
    last_matched_pattern: str = ""
    source_instinct_ids: list[str] = Field(default_factory=list)
    pattern_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LearningStatusSnapshot(FlexibleModel):
    """Aggregated status shown by the CLI."""

    enabled: bool = False
    strict_privacy: bool = True
    require_human_approval: bool = True
    auto_activate: bool = False
    observations: int = 0
    instincts: int = 0
    drafts: int = 0
    approved_drafts: int = 0
    rejected_drafts: int = 0
    active_skills: list[str] = Field(default_factory=list)
    skills_needing_review: list[str] = Field(default_factory=list)
    last_observation_at: datetime | None = None
