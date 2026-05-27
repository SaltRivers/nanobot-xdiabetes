"""Pydantic schemas for the Foundation Agent workflow.

These schemas structure the clinical reasoning process, making the agent's
decision-making explicit, traceable, and guideline-grounded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    """Base model that accepts extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow")


class ClinicalTaskPlan(FlexibleModel):
    """Structured decomposition of a user query into clinical tasks.

    This schema captures the agent's understanding of what the user is asking
    and what clinical workflow should be followed.
    """

    original_query: str
    task_type: str = Field(
        description="Clinical task category: screening, prediction, management, "
        "treatment_planning, risk_assessment, trajectory_analysis, etc."
    )
    audience: Literal["doctor", "patient"] = "doctor"
    patient_reference: str = Field(
        default="",
        description="Patient identifier or reference from the query"
    )
    sub_tasks: list[str] = Field(
        default_factory=list,
        description="Decomposed sub-tasks if the query is complex"
    )
    required_data: list[str] = Field(
        default_factory=list,
        description="Data modalities needed: demographics, labs, imaging, cgm, etc."
    )
    required_dtmh_capability: str = Field(
        default="diabetes_screening",
        description="DTMH capability needed: diabetes_screening, subtype_classification, "
        "complication_prediction, trajectory_prediction, treatment_response, etc."
    )


class GuidelinePlan(FlexibleModel):
    """Guideline-based clinical workflow plan.

    This schema represents the agent's clinical reasoning about how to approach
    the task, following medical guidelines and expert workflow patterns.
    """

    clinical_steps: list[str] = Field(
        default_factory=list,
        description="Ordered clinical workflow steps to execute"
    )
    guideline_basis: list[str] = Field(
        default_factory=list,
        description="Clinical guidelines or standards referenced"
    )
    required_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence types needed: literature, guidelines, cohort studies, etc."
    )
    required_safety_checks: list[str] = Field(
        default_factory=list,
        description="Safety validations required before proceeding"
    )
    expected_dtmh_outputs: list[str] = Field(
        default_factory=list,
        description="Expected output types from DTMH: risk_scores, trajectories, "
        "medication_recommendations, etc."
    )


class DataPreparationResult(FlexibleModel):
    """Result of patient data preparation and validation.

    This schema captures data quality assessment and DTMH-ready payload status.
    """

    patient_id: str
    available_modalities: list[str] = Field(
        default_factory=list,
        description="Data modalities present: demographics, labs, imaging, cgm, etc."
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Required fields that are missing"
    )
    temporal_coverage: dict[str, Any] = Field(
        default_factory=dict,
        description="Time range and frequency of available data"
    )
    dtmh_ready: bool = Field(
        default=False,
        description="Whether data is ready for DTMH inference"
    )
    payload_preview: dict[str, Any] = Field(
        default_factory=dict,
        description="Preview of prepared DTMH request payload"
    )
    data_quality_flags: list[str] = Field(
        default_factory=list,
        description="Data quality warnings or issues"
    )


class DTMHExecutionPlan(FlexibleModel):
    """Structured plan for DTMH model execution.

    This schema maps clinical tasks to specific DTMH capabilities and
    configures the inference request.
    """

    capability: str = Field(
        default="diabetes_screening",
        description="DTMH capability: diabetes_screening, subtype_classification, "
        "complication_prediction, trajectory_prediction, treatment_response, "
        "medication_next_time, medication_type, medication_dose, unified_representation"
    )
    output_heads: list[str] = Field(
        default_factory=list,
        description="Specific output heads to request from DTMH"
    )
    request_format: str = Field(
        default="dtcan_predict_csv",
        description="DTMH API format: dtcan_predict_csv, unified_inference, etc."
    )
    cohort_dir: str = Field(
        default="",
        description="Path to patient cohort directory"
    )
    patient_id: int | str = Field(
        default="",
        description="Patient identifier within cohort"
    )
    checkpoint_path: str = Field(
        default="",
        description="DTMH model checkpoint path"
    )
    config_path: str = Field(
        default="",
        description="DTMH model configuration path"
    )
    time_horizon: str = Field(
        default="",
        description="Prediction time horizon if applicable"
    )
    intervention_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Intervention or treatment context for counterfactual analysis"
    )
    return_latents: bool = Field(
        default=False,
        description="Whether to return latent representations"
    )
    return_uncertainty: bool = Field(
        default=False,
        description="Whether to return uncertainty estimates"
    )


class ClinicalInterpretation(FlexibleModel):
    """Clinical interpretation of DTMH model outputs.

    This schema transforms raw model predictions into clinically meaningful
    insights with proper medical terminology and context.
    """

    main_conclusion: str = Field(
        description="Primary clinical conclusion in natural language"
    )
    risk_level: str = Field(
        default="unknown",
        description="Overall risk assessment: low, moderate, high, critical"
    )
    model_outputs_used: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw model outputs that informed the interpretation"
    )
    uncertainty: dict[str, Any] = Field(
        default_factory=dict,
        description="Uncertainty quantification and confidence intervals"
    )
    data_limitations: list[str] = Field(
        default_factory=list,
        description="Data quality issues that may affect interpretation"
    )
    recommended_next_actions: list[str] = Field(
        default_factory=list,
        description="Clinical recommendations: further testing, follow-up, interventions"
    )
    evidence_basis: list[str] = Field(
        default_factory=list,
        description="Supporting evidence from guidelines or literature"
    )


class ReflectionDecision(FlexibleModel):
    """Reflective decision about workflow completion and next steps.

    This schema enables the agent to assess whether the task is complete
    or requires additional iterations.
    """

    is_complete: bool = Field(
        description="Whether the clinical task is fully addressed"
    )
    reason: str = Field(
        description="Explanation of why the task is complete or incomplete"
    )
    failure_modes: list[str] = Field(
        default_factory=list,
        description="Issues encountered: insufficient_data, conflicting_evidence, "
        "model_uncertainty, missing_context, etc."
    )
    next_action: str = Field(
        default="finalize",
        description="Next step: finalize, retrieve_evidence, fetch_data, "
        "rerun_dtmh, escalate, request_clarification"
    )
    additional_queries: list[str] = Field(
        default_factory=list,
        description="Follow-up queries to execute if not complete"
    )


class FoundationTrace(FlexibleModel):
    """Complete execution trace of a Foundation Agent workflow run.

    This schema captures the entire clinical reasoning process for debugging,
    auditing, and research demonstration.
    """

    trace_id: str
    patient_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    original_query: str

    # Phase 1: Planning
    task_plan: ClinicalTaskPlan | None = None
    guideline_plan: GuidelinePlan | None = None
    planning_duration_ms: int = 0

    # Phase 2: Data Preparation
    data_preparation: DataPreparationResult | None = None
    data_prep_duration_ms: int = 0

    # Phase 3: DTMH Execution
    dtmh_plan: DTMHExecutionPlan | None = None
    dtmh_request: dict[str, Any] = Field(default_factory=dict)
    dtmh_response: dict[str, Any] = Field(default_factory=dict)
    dtmh_duration_ms: int = 0
    dtmh_backend: str = ""

    # Phase 4: Interpretation
    interpretation: ClinicalInterpretation | None = None
    evidence_retrieved: list[dict[str, Any]] = Field(default_factory=list)
    interpretation_duration_ms: int = 0

    # Phase 5: Reflection
    reflection: ReflectionDecision | None = None
    reflection_duration_ms: int = 0

    # Final Output
    report_path: str = ""
    report_saved: bool = False

    # Metadata
    total_duration_ms: int = 0
    workflow_version: str = "foundation_v1"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
