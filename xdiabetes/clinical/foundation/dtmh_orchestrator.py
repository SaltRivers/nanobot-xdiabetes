"""DTMH capability orchestration and execution.

This module maps clinical tasks to appropriate DTMH capabilities and
manages model inference execution.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from xdiabetes.clinical.adapters.base import DTMHAdapter
from xdiabetes.clinical.foundation.schemas import (
    ClinicalTaskPlan,
    DTMHExecutionPlan,
    DataPreparationResult,
)
from xdiabetes.clinical.schemas import DTMHRequest, PatientCase


class DTMHOrchestrator:
    """DTMH capability selection and execution orchestrator.

    This class maps clinical tasks to DTMH model capabilities, configures
    inference parameters, and executes model calls through the adapter layer.
    """

    # DTMH capability configurations
    CAPABILITY_CONFIGS = {
        "diabetes_screening": {
            "output_heads": ["diabetes_probability"],
            "checkpoint_suffix": "deepdr_ehr_text",
            "config_suffix": "deepdr_ehr_text",
            "description": "Binary diabetes screening from multimodal data",
        },
        "subtype_classification": {
            "output_heads": ["subtype_probabilities"],
            "checkpoint_suffix": "subtype_classifier",
            "config_suffix": "subtype_classifier",
            "description": "Diabetes subtype classification (T1D, T2D, gestational)",
        },
        "complication_prediction": {
            "output_heads": ["organ_risk_scores", "complication_probabilities"],
            "checkpoint_suffix": "complication_predictor",
            "config_suffix": "complication_predictor",
            "description": "Multi-organ complication risk prediction",
        },
        "trajectory_prediction": {
            "output_heads": ["trajectory_prediction", "progression_rate"],
            "checkpoint_suffix": "trajectory_model",
            "config_suffix": "trajectory_model",
            "description": "Longitudinal disease trajectory prediction",
        },
        "treatment_response": {
            "output_heads": ["treatment_response_prediction"],
            "checkpoint_suffix": "treatment_response",
            "config_suffix": "treatment_response",
            "description": "Treatment efficacy prediction",
        },
        "medication_type": {
            "output_heads": ["medication_ranking", "efficacy_prediction"],
            "checkpoint_suffix": "medication_recommender",
            "config_suffix": "medication_recommender",
            "description": "Medication recommendation and ranking",
        },
        "medication_dose": {
            "output_heads": ["dose_recommendation"],
            "checkpoint_suffix": "dose_optimizer",
            "config_suffix": "dose_optimizer",
            "description": "Medication dosage optimization",
        },
        "medication_next_time": {
            "output_heads": ["next_medication_time"],
            "checkpoint_suffix": "timing_optimizer",
            "config_suffix": "timing_optimizer",
            "description": "Medication timing optimization",
        },
        "unified_representation": {
            "output_heads": ["latent_representation"],
            "checkpoint_suffix": "unified_encoder",
            "config_suffix": "unified_encoder",
            "description": "Unified patient representation learning",
        },
    }

    # Default checkpoint and config paths
    DEFAULT_CHECKPOINT_BASE = "checkpoints"
    DEFAULT_CONFIG_BASE = "src/configs"

    def __init__(self, dtmh_adapter: DTMHAdapter | None = None):
        """Initialize the DTMH orchestrator.

        Args:
            dtmh_adapter: Optional DTMH adapter for model inference
        """
        self._dtmh_adapter = dtmh_adapter

    async def create_execution_plan(
        self,
        task_plan: ClinicalTaskPlan,
        data_result: DataPreparationResult,
        context: dict[str, Any] | None = None,
    ) -> DTMHExecutionPlan:
        """Create DTMH execution plan from clinical task.

        Args:
            task_plan: Clinical task plan
            data_result: Prepared data result
            context: Optional context information

        Returns:
            DTMHExecutionPlan with DTMH configuration
        """
        logger.debug(
            "Creating DTMH execution plan: capability={} patient={}",
            task_plan.required_dtmh_capability,
            task_plan.patient_reference,
        )

        # Get capability configuration
        capability = task_plan.required_dtmh_capability
        capability_config = self.CAPABILITY_CONFIGS.get(
            capability,
            self.CAPABILITY_CONFIGS["diabetes_screening"],
        )

        # Determine request format based on data mode
        request_format = self._determine_request_format(data_result)

        # Build checkpoint and config paths
        checkpoint_path = self._build_checkpoint_path(capability, context)
        config_path = self._build_config_path(capability, context)

        # Extract cohort_dir and patient_id from data result
        cohort_dir = ""
        patient_id = data_result.patient_id

        if data_result.payload_preview.get("mode") == "csv":
            cohort_dir = data_result.payload_preview.get("cohort_dir", "")
            patient_id = data_result.payload_preview.get("patient_id", patient_id)

        # Determine output heads
        output_heads = capability_config["output_heads"]

        # Build execution plan
        execution_plan = DTMHExecutionPlan(
            capability=capability,
            output_heads=output_heads,
            request_format=request_format,
            cohort_dir=cohort_dir,
            patient_id=patient_id,
            checkpoint_path=checkpoint_path,
            config_path=config_path,
            time_horizon="",  # Future: extract from task_plan
            intervention_context={},  # Future: extract from task_plan
            return_latents=False,  # Future: configurable
            return_uncertainty=True,  # Always return uncertainty for safety
        )

        logger.debug(
            "DTMH execution plan created: format={} checkpoint={}",
            request_format,
            checkpoint_path,
        )

        return execution_plan

    async def execute_dtmh(
        self,
        execution_plan: DTMHExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute DTMH inference with the given plan.

        Args:
            execution_plan: DTMH execution plan
            context: Optional context information

        Returns:
            Raw DTMH response dictionary
        """
        if not self._dtmh_adapter:
            raise RuntimeError("DTMH adapter not configured")

        logger.debug(
            "Executing DTMH inference: capability={} patient={}",
            execution_plan.capability,
            execution_plan.patient_id,
        )

        # Build PatientCase based on request format
        if execution_plan.request_format == "dtcan_predict_csv":
            # CSV mode: minimal PatientCase as carrier
            patient_case = self._build_csv_patient_case(execution_plan)
        else:
            # Case mode: full PatientCase from context
            patient_case = self._build_case_patient_case(execution_plan, context)

        # Build DTMHRequest
        dtmh_request = DTMHRequest(
            patient=patient_case,
            task=self._map_capability_to_task(execution_plan.capability),
            clinical_question=self._generate_clinical_question(execution_plan),
            audience="doctor",  # Foundation Agent is always doctor-facing
        )

        # Execute DTMH inference
        result = self._dtmh_adapter.analyze(dtmh_request)

        logger.debug(
            "DTMH inference completed: backend={} patient={}",
            result.backend,
            result.patient_id,
        )

        # Return as dictionary
        return result.model_dump(mode="json")

    def _determine_request_format(
        self,
        data_result: DataPreparationResult,
    ) -> str:
        """Determine DTMH request format based on data mode."""
        if data_result.payload_preview.get("mode") == "csv":
            return "dtcan_predict_csv"
        return "dtcan_predict"

    def _build_checkpoint_path(
        self,
        capability: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build checkpoint path for the given capability.

        For MVP, returns empty string to use adapter defaults.
        Future: construct from capability config.
        """
        # Check for explicit override in context
        if context and "checkpoint_path" in context:
            return context["checkpoint_path"]

        # For MVP, use adapter defaults (empty string)
        # Future: construct from capability config
        # capability_config = self.CAPABILITY_CONFIGS.get(capability, {})
        # checkpoint_suffix = capability_config.get("checkpoint_suffix", "deepdr_ehr_text")
        # return f"{self.DEFAULT_CHECKPOINT_BASE}/{checkpoint_suffix}/best.pt"

        return ""

    def _build_config_path(
        self,
        capability: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build config path for the given capability.

        For MVP, returns empty string to use adapter defaults.
        Future: construct from capability config.
        """
        # Check for explicit override in context
        if context and "config_path" in context:
            return context["config_path"]

        # For MVP, use adapter defaults (empty string)
        # Future: construct from capability config
        # capability_config = self.CAPABILITY_CONFIGS.get(capability, {})
        # config_suffix = capability_config.get("config_suffix", "deepdr_ehr_text")
        # return f"{self.DEFAULT_CONFIG_BASE}/{config_suffix}.yaml"

        return ""

    def _build_csv_patient_case(
        self,
        execution_plan: DTMHExecutionPlan,
    ) -> PatientCase:
        """Build minimal PatientCase for CSV mode."""
        return PatientCase(
            patient_id=str(execution_plan.patient_id),
            metadata={
                "cohort_dir": execution_plan.cohort_dir,
                "patient_id_csv": execution_plan.patient_id,
            },
        )

    def _build_case_patient_case(
        self,
        execution_plan: DTMHExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> PatientCase:
        """Build full PatientCase from context data.

        For MVP, this is a placeholder. Future implementation will
        extract patient data from context.
        """
        # Future: extract from context["patient_data"]
        return PatientCase(
            patient_id=str(execution_plan.patient_id),
            metadata={},
        )

    def _map_capability_to_task(self, capability: str) -> str:
        """Map DTMH capability to task string."""
        capability_to_task = {
            "diabetes_screening": "screening",
            "subtype_classification": "subtyping",
            "complication_prediction": "complication",
            "trajectory_prediction": "followup",
            "treatment_response": "management",
            "medication_type": "management",
            "medication_dose": "management",
            "medication_next_time": "management",
            "unified_representation": "general",
        }
        return capability_to_task.get(capability, "general")

    def _generate_clinical_question(
        self,
        execution_plan: DTMHExecutionPlan,
    ) -> str:
        """Generate clinical question from execution plan."""
        capability_config = self.CAPABILITY_CONFIGS.get(
            execution_plan.capability,
            {},
        )
        description = capability_config.get("description", "Clinical analysis")
        return f"{description} for patient {execution_plan.patient_id}"
