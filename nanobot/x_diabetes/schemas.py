"""Pydantic schemas used by the X-Diabetes runtime.

The schemas are intentionally permissive: we validate the contract we need for
runtime safety, while still allowing extra fields so future datasets or agents
can extend the patient representation without breaking compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    """Base model that accepts extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow")


class PatientCase(FlexibleModel):
    """Minimal patient record used by the local MVP workflow."""

    patient_id: str
    demographics: dict[str, Any] = Field(default_factory=dict)
    vitals: dict[str, Any] = Field(default_factory=dict)
    labs: dict[str, Any] = Field(default_factory=dict)
    cgm: dict[str, Any] = Field(default_factory=dict)
    imaging: dict[str, Any] = Field(default_factory=dict)
    medications: list[Any] = Field(default_factory=list)
    history: dict[str, Any] = Field(default_factory=dict)
    complications: list[Any] | dict[str, Any] = Field(default_factory=list)
    notes: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatientContext(FlexibleModel):
    """Standardized patient context returned to the agent layer."""

    patient_id: str
    summary: str
    available_modalities: list[str] = Field(default_factory=list)
    missing_modalities: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    longitudinal_summary: str = ""
    recent_events: list["PatientTimelineEvent"] = Field(default_factory=list)
    structured_data: dict[str, Any] = Field(default_factory=dict)


class KnowledgeHit(FlexibleModel):
    """One knowledge-base match returned by local retrieval."""

    knowledge_id: str
    title: str
    source: str = "local"
    summary: str
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0
    file_path: str = ""
    snippet: str = ""


class KnowledgeRetrievalMetadata(FlexibleModel):
    """Trace metadata for one knowledge retrieval attempt."""

    backend_requested: str = "local"
    backend_used: str = "local"
    status: str = "empty"
    latency_ms: int = 0
    warning: str = ""
    result_count: int = 0


class KnowledgeRetrievalResult(FlexibleModel):
    """Structured retrieval result with hits and execution metadata."""

    hits: list[KnowledgeHit] = Field(default_factory=list)
    metadata: KnowledgeRetrievalMetadata = Field(default_factory=KnowledgeRetrievalMetadata)


class SafetyFlag(FlexibleModel):
    """One safety warning emitted by the rule engine."""

    severity: Literal["info", "warning", "critical"]
    code: str
    message: str
    recommendation: str


class SafetyAssessment(FlexibleModel):
    """Safety gate output consumed by the report builder and the agent."""

    overall_status: Literal["pass", "review", "escalate"]
    flags: list[SafetyFlag] = Field(default_factory=list)
    disclaimer: str = ""


class DTMHRequest(FlexibleModel):
    """Stable request contract for all DTMH adapters."""

    patient: PatientCase
    task: str = "general"
    clinical_question: str = ""
    audience: Literal["doctor", "patient"] = "doctor"


class DTMHResult(FlexibleModel):
    """Adapter-neutral response contract for DTMH analysis."""

    patient_id: str
    backend: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str
    model_version: str = "unavailable"
    organ_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    risk_profile: dict[str, Any] = Field(default_factory=dict)
    recommended_next_steps: list[str] = Field(default_factory=list)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PatientMemoryProfile(FlexibleModel):
    """Persistent patient-level profile used by the longitudinal memory store."""

    patient_id: str
    demographics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PatientTimelineEvent(FlexibleModel):
    """One longitudinal event attached to a patient."""

    event_id: str
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    task: str = "general"
    title: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class PatientLongitudinalSnapshot(FlexibleModel):
    """Latest workflow-derived state snapshot for a patient."""

    patient_id: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latest_task: str = "general"
    latest_clinical_question: str = ""
    latest_report_path: str = ""
    latest_safety_status: str = ""
    latest_dtmh_backend: str = ""
    latest_patient_summary: str = ""
    latest_risk_profile: dict[str, Any] = Field(default_factory=dict)
    latest_data_quality_flags: list[str] = Field(default_factory=list)


class EncounterRecord(FlexibleModel):
    """Structured record of one completed consultation or workflow run."""

    encounter_id: str
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    task: str = "general"
    audience: Literal["doctor", "patient"] = "doctor"
    clinical_question: str = ""
    patient_summary: str = ""
    report_path: str = ""
    report_saved: bool = False
    safety_status: str = "pass"
    safety_flags: list[SafetyFlag] = Field(default_factory=list)
    dtmh_backend: str = ""
    evidence_titles: list[str] = Field(default_factory=list)
    knowledge_metadata: KnowledgeRetrievalMetadata = Field(default_factory=KnowledgeRetrievalMetadata)
    data_quality_flags: list[str] = Field(default_factory=list)


class RiskAssessmentRecord(FlexibleModel):
    """Persistent structured risk snapshot from one workflow run."""

    assessment_id: str
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    task: str = "general"
    dtmh_backend: str = ""
    overall_status: str = "pass"
    risk_profile: dict[str, Any] = Field(default_factory=dict)
    organ_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    safety_flags: list[SafetyFlag] = Field(default_factory=list)


class ReportArtifact(FlexibleModel):
    """Persisted report information returned by report generation."""

    audience: Literal["doctor", "patient"]
    markdown: str
    saved_path: str = ""


class ReportIndexRecord(FlexibleModel):
    """Minimal index entry that points to a generated report artifact."""

    report_id: str
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    task: str = "general"
    audience: Literal["doctor", "patient"]
    report_path: str
    report_type: str = "consultation"


class ConsultationResult(FlexibleModel):
    """High-level consultation result used by the primary tool."""

    patient_context: PatientContext
    dtmh_result: DTMHResult
    evidence: list[KnowledgeHit] = Field(default_factory=list)
    knowledge_metadata: KnowledgeRetrievalMetadata = Field(default_factory=KnowledgeRetrievalMetadata)
    safety: SafetyAssessment
    report: ReportArtifact
