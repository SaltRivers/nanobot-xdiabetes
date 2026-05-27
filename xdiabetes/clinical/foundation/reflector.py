"""Reflective decision-making and workflow iteration.

This module implements the reflection loop that determines whether
the workflow is complete or requires additional iterations.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from xdiabetes.clinical.foundation.schemas import (
    ClinicalInterpretation,
    ClinicalTaskPlan,
    ReflectionDecision,
)


class WorkflowReflector:
    """Reflective decision engine for workflow completion assessment.

    This class evaluates whether the clinical workflow has produced
    sufficient, high-quality results or requires additional iterations,
    evidence retrieval, or data collection.
    """

    # Failure mode patterns and their triggers
    FAILURE_MODE_TRIGGERS = {
        "insufficient_data": [
            "missing_critical_field",
            "no_patient_data_provided",
            "missing_patient_id",
        ],
        "data_quality_issues": [
            "invalid_age_range",
            "invalid_age_format",
            "sparse_data",
        ],
        "model_uncertainty": [
            "unknown",  # risk level
        ],
        "conflicting_evidence": [
            # Future: detect conflicts between model output and guidelines
        ],
        "missing_context": [
            # Future: detect when additional patient context is needed
        ],
    }

    # Next action mapping by failure mode
    FAILURE_MODE_ACTIONS = {
        "insufficient_data": "fetch_data",
        "data_quality_issues": "validate_data",
        "model_uncertainty": "retrieve_evidence",
        "conflicting_evidence": "retrieve_evidence",
        "missing_context": "request_clarification",
    }

    # Task types that require evidence augmentation
    EVIDENCE_REQUIRED_TASKS = [
        "treatment_planning",
        "medication_recommendation",
        "complication_prediction",
    ]

    def __init__(self):
        """Initialize the workflow reflector."""
        pass

    async def reflect(
        self,
        task_plan: ClinicalTaskPlan,
        interpretation: ClinicalInterpretation,
        context: dict[str, Any] | None = None,
    ) -> ReflectionDecision:
        """Assess workflow completion and determine next steps.

        Args:
            task_plan: Original clinical task plan
            interpretation: Clinical interpretation result
            context: Optional context information

        Returns:
            ReflectionDecision with completion status and next actions
        """
        logger.debug(
            "Reflecting on workflow: task={} risk={}",
            task_plan.task_type,
            interpretation.risk_level,
        )

        # Detect failure modes
        failure_modes = self._detect_failure_modes(
            task_plan,
            interpretation,
            context,
        )

        # Assess completeness
        is_complete = self._assess_completeness(
            task_plan,
            interpretation,
            failure_modes,
            context,
        )

        # Generate reason
        reason = self._generate_reason(
            task_plan,
            interpretation,
            is_complete,
            failure_modes,
        )

        # Determine next action
        next_action = self._determine_next_action(
            is_complete,
            failure_modes,
            task_plan,
        )

        # Generate additional queries if needed
        additional_queries = self._generate_additional_queries(
            next_action,
            failure_modes,
            task_plan,
        )

        decision = ReflectionDecision(
            is_complete=is_complete,
            reason=reason,
            failure_modes=failure_modes,
            next_action=next_action,
            additional_queries=additional_queries,
        )

        logger.debug(
            "Reflection completed: complete={} next_action={} failure_modes={}",
            is_complete,
            next_action,
            len(failure_modes),
        )

        return decision

    def _detect_failure_modes(
        self,
        task_plan: ClinicalTaskPlan,
        interpretation: ClinicalInterpretation,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Detect failure modes from interpretation and context."""
        failure_modes = []

        # Check data limitations
        data_limitations = interpretation.data_limitations
        for limitation in data_limitations:
            for mode, triggers in self.FAILURE_MODE_TRIGGERS.items():
                if any(trigger in limitation for trigger in triggers):
                    if mode not in failure_modes:
                        failure_modes.append(mode)

        # Check model uncertainty
        if interpretation.risk_level == "unknown":
            failure_modes.append("model_uncertainty")

        # Check uncertainty level
        uncertainty = interpretation.uncertainty
        if isinstance(uncertainty, dict):
            uncertainty_level = uncertainty.get("level", "moderate")
            if uncertainty_level in ["high", "very_high"]:
                if "model_uncertainty" not in failure_modes:
                    failure_modes.append("model_uncertainty")

        # Check for missing critical outputs
        model_outputs = interpretation.model_outputs_used
        if not model_outputs or len(model_outputs) < 2:
            failure_modes.append("insufficient_model_output")

        # Check for sub-task completion
        if task_plan.sub_tasks and context:
            completed_subtasks = context.get("completed_subtasks", [])
            if len(completed_subtasks) < len(task_plan.sub_tasks):
                failure_modes.append("incomplete_subtasks")

        return failure_modes

    def _assess_completeness(
        self,
        task_plan: ClinicalTaskPlan,
        interpretation: ClinicalInterpretation,
        failure_modes: list[str],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Assess whether the workflow is complete."""
        # Check for blocking failure modes
        blocking_modes = [
            "insufficient_data",
            "missing_context",
        ]

        for mode in blocking_modes:
            if mode in failure_modes:
                return False

        # Check for critical data quality issues
        if "data_quality_issues" in failure_modes:
            # Only blocking if critical fields are affected
            data_limitations = interpretation.data_limitations
            critical_issues = [
                "missing_critical_field",
                "invalid_age_format",
            ]
            if any(issue in str(data_limitations) for issue in critical_issues):
                return False

        # Check if sub-tasks are complete
        if "incomplete_subtasks" in failure_modes:
            return False

        # Check if evidence is required but missing
        if task_plan.task_type in self.EVIDENCE_REQUIRED_TASKS:
            evidence_basis = interpretation.evidence_basis
            if not evidence_basis or len(evidence_basis) < 2:
                # For MVP, we accept guideline references without retrieval
                # Future: require actual evidence retrieval
                pass

        # Check if interpretation has actionable recommendations
        if not interpretation.recommended_next_actions:
            return False

        # Check if risk level is determined
        if interpretation.risk_level == "unknown":
            return False

        # If no blocking issues, workflow is complete
        return True

    def _generate_reason(
        self,
        task_plan: ClinicalTaskPlan,
        interpretation: ClinicalInterpretation,
        is_complete: bool,
        failure_modes: list[str],
    ) -> str:
        """Generate human-readable reason for completion status."""
        if is_complete:
            # Generate completion reason
            task_type = task_plan.task_type
            risk_level = interpretation.risk_level

            if task_type == "screening":
                return (
                    f"Diabetes screening completed with {risk_level} risk assessment. "
                    "DTMH model inference and clinical interpretation are sufficient "
                    "for clinical decision support."
                )
            elif task_type == "risk_assessment":
                return (
                    f"Risk assessment completed with {risk_level} risk stratification. "
                    "Complication risk analysis and recommendations are ready for review."
                )
            elif task_type == "complication_prediction":
                return (
                    f"Complication prediction completed with {risk_level} risk level. "
                    "Organ-specific risk assessment and specialist referral recommendations provided."
                )
            else:
                return (
                    f"Clinical workflow completed for {task_type} task. "
                    "Analysis and recommendations are ready for clinical review."
                )
        else:
            # Generate incompletion reason
            if "insufficient_data" in failure_modes:
                return (
                    "Workflow incomplete due to insufficient patient data. "
                    "Critical fields are missing and must be provided before DTMH inference."
                )
            elif "missing_context" in failure_modes:
                return (
                    "Workflow incomplete due to missing clinical context. "
                    "Additional patient information or clarification is required."
                )
            elif "incomplete_subtasks" in failure_modes:
                return (
                    "Workflow incomplete due to pending sub-tasks. "
                    "All sub-tasks must be completed before finalizing the analysis."
                )
            elif "model_uncertainty" in failure_modes:
                return (
                    "Workflow incomplete due to high model uncertainty. "
                    "Additional evidence retrieval or data validation is recommended."
                )
            elif "data_quality_issues" in failure_modes:
                return (
                    "Workflow incomplete due to data quality issues. "
                    "Data validation and correction are required before proceeding."
                )
            else:
                return (
                    "Workflow incomplete due to unresolved issues. "
                    "Review failure modes and address identified problems."
                )

    def _determine_next_action(
        self,
        is_complete: bool,
        failure_modes: list[str],
        task_plan: ClinicalTaskPlan,
    ) -> str:
        """Determine the next action based on completion status."""
        if is_complete:
            return "finalize"

        # Map failure modes to actions
        for mode in failure_modes:
            action = self.FAILURE_MODE_ACTIONS.get(mode)
            if action:
                return action

        # Default action for incomplete workflows
        return "escalate"

    def _generate_additional_queries(
        self,
        next_action: str,
        failure_modes: list[str],
        task_plan: ClinicalTaskPlan,
    ) -> list[str]:
        """Generate additional queries for incomplete workflows."""
        queries = []

        if next_action == "fetch_data":
            queries.append(
                f"Retrieve missing patient data for patient {task_plan.patient_reference}"
            )

        elif next_action == "validate_data":
            queries.append(
                f"Validate and correct data quality issues for patient {task_plan.patient_reference}"
            )

        elif next_action == "retrieve_evidence":
            queries.append(
                f"Retrieve supporting clinical evidence for {task_plan.task_type} task"
            )

        elif next_action == "request_clarification":
            queries.append(
                f"Request additional clinical context for patient {task_plan.patient_reference}"
            )

        elif next_action == "rerun_dtmh":
            queries.append(
                f"Re-execute DTMH inference with corrected data for patient {task_plan.patient_reference}"
            )

        # Add sub-task queries if incomplete
        if "incomplete_subtasks" in failure_modes and task_plan.sub_tasks:
            for subtask in task_plan.sub_tasks:
                queries.append(f"Complete sub-task: {subtask}")

        return queries
