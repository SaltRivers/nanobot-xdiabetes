"""Foundation Agent main workflow controller.

This module orchestrates the complete clinical reasoning workflow:
Query → Planning → Data Prep → DTMH → Interpretation → Reflection → Report
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from xdiabetes.clinical.adapters.base import DTMHAdapter
from xdiabetes.clinical.foundation.schemas import (
    ClinicalInterpretation,
    ClinicalTaskPlan,
    DTMHExecutionPlan,
    DataPreparationResult,
    FoundationTrace,
    GuidelinePlan,
    ReflectionDecision,
)
from xdiabetes.clinical.schemas import DTMHRequest, PatientCase


class FoundationWorkflow:
    """Main Foundation Agent workflow orchestrator.

    This class coordinates the guideline-grounded clinical reasoning process,
    transforming user queries into structured clinical analysis.
    """

    def __init__(self, dtmh_adapter: DTMHAdapter | None = None):
        """Initialize the Foundation Agent workflow.

        Args:
            dtmh_adapter: Optional DTMH adapter for model inference
        """
        self._dtmh_adapter = dtmh_adapter

    async def execute(
        self,
        query: str,
        patient_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> FoundationTrace:
        """Execute the complete Foundation Agent workflow.

        Args:
            query: User's clinical query
            patient_data: Optional patient data dictionary
            context: Optional execution context

        Returns:
            FoundationTrace with complete workflow execution record
        """
        trace_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info("Foundation Agent workflow started: trace_id={}", trace_id)

        # Phase 1: Query decomposition and guideline planning
        planning_start = time.time()
        task_plan = await self._decompose_query(query, context)
        guideline_plan = await self._plan_workflow(task_plan, context)
        planning_duration = int((time.time() - planning_start) * 1000)

        # Phase 2: Data preparation
        data_prep_start = time.time()
        data_result = await self._prepare_data(task_plan, patient_data, context)
        data_prep_duration = int((time.time() - data_prep_start) * 1000)

        # Phase 3: DTMH execution
        dtmh_start = time.time()
        dtmh_plan = await self._create_dtmh_plan(task_plan, data_result, context)
        dtmh_response = await self._execute_dtmh(dtmh_plan, context)
        dtmh_duration = int((time.time() - dtmh_start) * 1000)

        # Phase 4: Clinical interpretation
        interpretation_start = time.time()
        interpretation = await self._interpret_results(
            task_plan, dtmh_response, context
        )
        interpretation_duration = int((time.time() - interpretation_start) * 1000)

        # Phase 5: Reflection
        reflection_start = time.time()
        reflection = await self._reflect(task_plan, interpretation, context)
        reflection_duration = int((time.time() - reflection_start) * 1000)

        total_duration = int((time.time() - start_time) * 1000)

        trace = FoundationTrace(
            trace_id=trace_id,
            patient_id=task_plan.patient_reference or "unknown",
            original_query=query,
            task_plan=task_plan,
            guideline_plan=guideline_plan,
            planning_duration_ms=planning_duration,
            data_preparation=data_result,
            data_prep_duration_ms=data_prep_duration,
            dtmh_plan=dtmh_plan,
            dtmh_response=dtmh_response,
            dtmh_duration_ms=dtmh_duration,
            dtmh_backend=self._dtmh_adapter.backend_name if self._dtmh_adapter else "none",
            interpretation=interpretation,
            interpretation_duration_ms=interpretation_duration,
            reflection=reflection,
            reflection_duration_ms=reflection_duration,
            total_duration_ms=total_duration,
        )

        logger.info(
            "Foundation Agent workflow completed: trace_id={} duration={}ms",
            trace_id,
            total_duration,
        )

        return trace

    async def _decompose_query(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ClinicalTaskPlan:
        """Decompose user query into structured clinical task (MVP implementation).

        For MVP, this uses simple pattern matching to extract cohort_dir and patient_id
        from queries like: "Check whether patient 4 in Dataset/private_fundus has diabetes"
        """
        # Extract patient ID
        patient_id_match = re.search(r"patient\s+(\d+)", query, re.IGNORECASE)
        patient_id = patient_id_match.group(1) if patient_id_match else ""

        # Extract cohort directory
        cohort_match = re.search(
            r"(?:in|from)\s+([\w/._-]+(?:Dataset|dataset)[\w/._-]*)",
            query,
            re.IGNORECASE,
        )
        cohort_dir = cohort_match.group(1) if cohort_match else ""

        # Determine task type
        task_type = "screening"
        if any(word in query.lower() for word in ["screen", "check", "has diabetes"]):
            task_type = "screening"
        elif any(word in query.lower() for word in ["risk", "predict", "complication"]):
            task_type = "risk_assessment"
        elif any(word in query.lower() for word in ["manage", "treatment", "medication"]):
            task_type = "management"

        return ClinicalTaskPlan(
            original_query=query,
            task_type=task_type,
            audience="doctor",
            patient_reference=patient_id,
            required_data=["demographics", "labs", "imaging"] if cohort_dir else [],
            required_dtmh_capability="diabetes_screening",
        )

    async def _plan_workflow(
        self,
        task_plan: ClinicalTaskPlan,
        context: dict[str, Any] | None = None,
    ) -> GuidelinePlan:
        """Create guideline-based workflow plan (MVP implementation)."""
        clinical_steps = [
            "Load patient data from cohort",
            "Execute DTMH diabetes screening model",
            "Interpret diabetes probability",
            "Generate clinical report",
        ]

        guideline_basis = [
            "ADA Standards of Medical Care in Diabetes",
            "WHO Diabetes Diagnostic Criteria",
        ]

        return GuidelinePlan(
            clinical_steps=clinical_steps,
            guideline_basis=guideline_basis,
            required_evidence=["diabetes_screening_guidelines"],
            required_safety_checks=["data_quality", "model_uncertainty"],
            expected_dtmh_outputs=["diabetes_probability"],
        )

    async def _prepare_data(
        self,
        task_plan: ClinicalTaskPlan,
        patient_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> DataPreparationResult:
        """Prepare patient data for DTMH (MVP implementation)."""
        # For MVP, extract cohort_dir from query
        cohort_match = re.search(
            r"(?:in|from)\s+([\w/._-]+)",
            task_plan.original_query,
            re.IGNORECASE,
        )
        cohort_dir = cohort_match.group(1) if cohort_match else ""

        return DataPreparationResult(
            patient_id=task_plan.patient_reference,
            available_modalities=["cohort_csv"],
            missing_fields=[],
            temporal_coverage={},
            dtmh_ready=bool(cohort_dir and task_plan.patient_reference),
            payload_preview={
                "cohort_dir": cohort_dir,
                "patient_id": task_plan.patient_reference,
            },
            data_quality_flags=[],
        )

    async def _create_dtmh_plan(
        self,
        task_plan: ClinicalTaskPlan,
        data_result: DataPreparationResult,
        context: dict[str, Any] | None = None,
    ) -> DTMHExecutionPlan:
        """Create DTMH execution plan (MVP implementation)."""
        return DTMHExecutionPlan(
            capability="diabetes_screening",
            output_heads=["diabetes_probability"],
            request_format="dtcan_predict_csv",
            cohort_dir=data_result.payload_preview.get("cohort_dir", ""),
            patient_id=data_result.patient_id,
            checkpoint_path="",  # Will use adapter defaults
            config_path="",  # Will use adapter defaults
        )

    async def _execute_dtmh(
        self,
        execution_plan: DTMHExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute DTMH inference (MVP implementation)."""
        if not self._dtmh_adapter:
            raise RuntimeError("DTMH adapter not configured")

        # Build minimal PatientCase as carrier for cohort_dir + patient_id
        patient_case = PatientCase(
            patient_id=str(execution_plan.patient_id),
            metadata={
                "cohort_dir": execution_plan.cohort_dir,
                "patient_id_csv": execution_plan.patient_id,
            },
        )

        # Call DTMH adapter
        result = self._dtmh_adapter.analyze(
            DTMHRequest(
                patient=patient_case,
                task="screening",
                clinical_question="Diabetes screening",
                audience="doctor",
            )
        )

        return result.model_dump(mode="json")

    async def _interpret_results(
        self,
        task_plan: ClinicalTaskPlan,
        dtmh_response: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ClinicalInterpretation:
        """Interpret DTMH results into clinical language (MVP implementation)."""
        # Extract diabetes probability
        risk_profile = dtmh_response.get("risk_profile", {})
        diabetes_prob_data = risk_profile.get("diabetes_probability", {})
        diabetes_prob = diabetes_prob_data.get("score", 0.0)
        prob_label = diabetes_prob_data.get("label", "unknown")

        # Determine risk level
        if diabetes_prob >= 0.8:
            risk_level = "high"
        elif diabetes_prob >= 0.5:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Generate clinical conclusion
        if diabetes_prob >= 0.8:
            conclusion = (
                f"Patient {task_plan.patient_reference} shows very high probability "
                f"({diabetes_prob:.1%}) of diabetes based on DTMH model analysis. "
                "Clinical confirmation with laboratory testing is strongly recommended."
            )
        elif diabetes_prob >= 0.5:
            conclusion = (
                f"Patient {task_plan.patient_reference} shows moderate to high probability "
                f"({diabetes_prob:.1%}) of diabetes. Further evaluation with HbA1c and "
                "fasting glucose is recommended."
            )
        else:
            conclusion = (
                f"Patient {task_plan.patient_reference} shows low probability "
                f"({diabetes_prob:.1%}) of diabetes based on current data. "
                "Continue routine monitoring as clinically appropriate."
            )

        # Recommended actions
        recommended_actions = dtmh_response.get("recommended_next_steps", [])
        if not recommended_actions:
            if diabetes_prob >= 0.5:
                recommended_actions = [
                    "Order HbA1c and fasting glucose tests",
                    "Review patient history and risk factors",
                    "Consider referral to endocrinology if confirmed",
                ]
            else:
                recommended_actions = [
                    "Continue routine screening per guidelines",
                    "Monitor for risk factor changes",
                ]

        return ClinicalInterpretation(
            main_conclusion=conclusion,
            risk_level=risk_level,
            model_outputs_used={
                "diabetes_probability": diabetes_prob,
                "probability_label": prob_label,
            },
            uncertainty={
                "level": "moderate",
                "note": "Model-based screening requires clinical validation",
            },
            data_limitations=dtmh_response.get("warnings", []),
            recommended_next_actions=recommended_actions,
            evidence_basis=[
                "ADA Standards of Medical Care in Diabetes",
                "DTMH model inference",
            ],
        )

    async def _reflect(
        self,
        task_plan: ClinicalTaskPlan,
        interpretation: ClinicalInterpretation,
        context: dict[str, Any] | None = None,
    ) -> ReflectionDecision:
        """Assess workflow completion (MVP implementation)."""
        # For MVP screening task, workflow is complete after interpretation
        is_complete = True
        reason = "Diabetes screening completed with DTMH model inference and clinical interpretation"

        # Check for potential issues
        failure_modes = []
        if interpretation.data_limitations:
            failure_modes.append("data_quality_warnings")

        return ReflectionDecision(
            is_complete=is_complete,
            reason=reason,
            failure_modes=failure_modes,
            next_action="finalize",
            additional_queries=[],
        )
