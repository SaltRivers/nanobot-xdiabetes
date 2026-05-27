"""Clinical interpretation of DTMH model outputs.

This module transforms raw model predictions into clinically meaningful
insights with proper medical terminology and evidence augmentation.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from xdiabetes.clinical.foundation.schemas import (
    ClinicalInterpretation,
    ClinicalTaskPlan,
)


class ClinicalInterpreter:
    """DTMH result interpretation and evidence augmentation engine.

    This class transforms raw DTMH model outputs into clinically meaningful
    interpretations with proper medical terminology, risk stratification,
    and actionable recommendations.
    """

    # Risk level thresholds by task type
    RISK_THRESHOLDS = {
        "screening": {
            "critical": 0.9,
            "high": 0.8,
            "moderate": 0.5,
            "low": 0.0,
        },
        "risk_assessment": {
            "critical": 0.8,
            "high": 0.6,
            "moderate": 0.4,
            "low": 0.0,
        },
        "complication_prediction": {
            "critical": 0.75,
            "high": 0.6,
            "moderate": 0.4,
            "low": 0.0,
        },
    }

    # Clinical recommendations by task type and risk level
    RECOMMENDATIONS = {
        "screening": {
            "critical": [
                "Immediate clinical evaluation with comprehensive metabolic panel",
                "Order HbA1c, fasting glucose, and OGTT for diagnostic confirmation",
                "Assess for acute complications and metabolic decompensation",
                "Consider urgent endocrinology referral",
            ],
            "high": [
                "Order HbA1c and fasting glucose tests for diagnostic confirmation",
                "Review patient history and risk factors in detail",
                "Schedule follow-up within 1-2 weeks",
                "Consider referral to endocrinology if confirmed",
            ],
            "moderate": [
                "Order confirmatory laboratory testing (HbA1c, fasting glucose)",
                "Review cardiovascular risk factors",
                "Schedule follow-up within 4 weeks",
            ],
            "low": [
                "Continue routine screening per ADA guidelines",
                "Monitor for risk factor changes",
                "Reinforce lifestyle modifications",
            ],
        },
        "risk_assessment": {
            "critical": [
                "Urgent evaluation for end-organ complications",
                "Comprehensive ophthalmology, nephrology, and cardiology assessment",
                "Intensify glycemic control and risk factor management",
                "Consider hospitalization if acute complications present",
            ],
            "high": [
                "Schedule comprehensive complication screening",
                "Optimize glycemic control and cardiovascular risk management",
                "Refer to appropriate specialists (ophthalmology, nephrology, cardiology)",
                "Increase monitoring frequency",
            ],
            "moderate": [
                "Annual comprehensive complication screening",
                "Optimize metabolic control",
                "Address modifiable risk factors",
            ],
            "low": [
                "Continue routine monitoring per guidelines",
                "Maintain current management plan",
                "Annual complication screening",
            ],
        },
        "complication_prediction": {
            "critical": [
                "Immediate specialist referral for high-risk organ systems",
                "Aggressive risk factor modification",
                "Consider advanced imaging or functional testing",
                "Intensify monitoring and follow-up",
            ],
            "high": [
                "Specialist referral for affected organ systems",
                "Optimize glycemic and blood pressure control",
                "Increase screening frequency for high-risk complications",
            ],
            "moderate": [
                "Enhanced monitoring for at-risk organ systems",
                "Optimize metabolic control",
                "Annual specialist evaluation",
            ],
            "low": [
                "Continue routine complication screening",
                "Maintain current management",
            ],
        },
    }

    # Evidence basis by task type
    EVIDENCE_BASIS = {
        "screening": [
            "ADA Standards of Medical Care in Diabetes",
            "DTMH multimodal screening model",
            "WHO Diabetes Diagnostic Criteria",
        ],
        "risk_assessment": [
            "ADA Standards of Medical Care in Diabetes",
            "DTMH complication prediction model",
            "UKPDS Risk Engine",
        ],
        "subtyping": [
            "ADA Classification of Diabetes",
            "DTMH subtype classification model",
        ],
        "complication_prediction": [
            "ADA Microvascular Complications Guidelines",
            "DTMH organ-specific risk prediction",
            "KDIGO, AAO, ACC/AHA Guidelines",
        ],
        "trajectory_analysis": [
            "DCCT/EDIC Study",
            "DTMH trajectory prediction model",
        ],
        "treatment_planning": [
            "ADA Pharmacologic Approaches to Glycemic Treatment",
            "DTMH treatment response model",
        ],
        "medication_recommendation": [
            "ADA/AACE Diabetes Management Algorithm",
            "DTMH medication recommendation model",
        ],
    }

    def __init__(self):
        """Initialize the clinical interpreter."""
        pass

    async def interpret_results(
        self,
        task_plan: ClinicalTaskPlan,
        dtmh_response: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ClinicalInterpretation:
        """Interpret DTMH outputs into clinical language.

        Args:
            task_plan: Clinical task plan
            dtmh_response: Raw DTMH response
            context: Optional context information

        Returns:
            ClinicalInterpretation with clinical insights
        """
        logger.debug(
            "Interpreting DTMH results: task={} patient={}",
            task_plan.task_type,
            task_plan.patient_reference,
        )

        # Extract model outputs
        model_outputs = self._extract_model_outputs(dtmh_response, task_plan)

        # Determine risk level
        risk_level = self._determine_risk_level(model_outputs, task_plan.task_type)

        # Generate clinical conclusion
        main_conclusion = self._generate_conclusion(
            task_plan,
            model_outputs,
            risk_level,
        )

        # Extract uncertainty information
        uncertainty = self._extract_uncertainty(dtmh_response)

        # Extract data limitations
        data_limitations = self._extract_limitations(dtmh_response)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            task_plan.task_type,
            risk_level,
            model_outputs,
        )

        # Get evidence basis
        evidence_basis = self.EVIDENCE_BASIS.get(
            task_plan.task_type,
            ["ADA Standards of Medical Care in Diabetes", "DTMH model inference"],
        )

        interpretation = ClinicalInterpretation(
            main_conclusion=main_conclusion,
            risk_level=risk_level,
            model_outputs_used=model_outputs,
            uncertainty=uncertainty,
            data_limitations=data_limitations,
            recommended_next_actions=recommendations,
            evidence_basis=evidence_basis,
        )

        logger.debug(
            "Interpretation completed: risk={} recommendations={}",
            risk_level,
            len(recommendations),
        )

        return interpretation

    def _extract_model_outputs(
        self,
        dtmh_response: dict[str, Any],
        task_plan: ClinicalTaskPlan,
    ) -> dict[str, Any]:
        """Extract relevant model outputs from DTMH response."""
        outputs = {}

        # Extract risk profile
        risk_profile = dtmh_response.get("risk_profile", {})

        # Extract diabetes probability (primary screening output)
        if "diabetes_probability" in risk_profile:
            diabetes_prob_data = risk_profile["diabetes_probability"]
            if isinstance(diabetes_prob_data, dict):
                outputs["diabetes_probability"] = diabetes_prob_data.get("score", 0.0)
                outputs["probability_label"] = diabetes_prob_data.get("label", "unknown")
            else:
                outputs["diabetes_probability"] = float(diabetes_prob_data)

        # Extract system probabilities
        if "system_probabilities" in risk_profile:
            outputs["system_probabilities"] = risk_profile["system_probabilities"]

        # Extract organ states
        organ_states = dtmh_response.get("organ_states", {})
        if organ_states:
            outputs["organ_states"] = organ_states

        # Extract summary
        outputs["summary"] = dtmh_response.get("summary", "")

        # Extract model version
        outputs["model_version"] = dtmh_response.get("model_version", "unknown")

        return outputs

    def _determine_risk_level(
        self,
        model_outputs: dict[str, Any],
        task_type: str,
    ) -> str:
        """Determine clinical risk level from model outputs."""
        # Get primary risk score
        primary_score = None

        if "diabetes_probability" in model_outputs:
            primary_score = model_outputs["diabetes_probability"]
        elif "system_probabilities" in model_outputs:
            # Use max system probability
            sys_probs = model_outputs["system_probabilities"]
            if isinstance(sys_probs, dict):
                primary_score = max(sys_probs.values()) if sys_probs else None

        if primary_score is None:
            return "unknown"

        # Get thresholds for task type
        thresholds = self.RISK_THRESHOLDS.get(
            task_type,
            self.RISK_THRESHOLDS["screening"],
        )

        # Determine risk level
        if primary_score >= thresholds["critical"]:
            return "critical"
        elif primary_score >= thresholds["high"]:
            return "high"
        elif primary_score >= thresholds["moderate"]:
            return "moderate"
        else:
            return "low"

    def _generate_conclusion(
        self,
        task_plan: ClinicalTaskPlan,
        model_outputs: dict[str, Any],
        risk_level: str,
    ) -> str:
        """Generate clinical conclusion in natural language."""
        patient_ref = task_plan.patient_reference or "the patient"
        task_type = task_plan.task_type

        # Get primary score
        diabetes_prob = model_outputs.get("diabetes_probability")

        if task_type == "screening":
            if diabetes_prob is not None:
                prob_pct = diabetes_prob * 100
                if risk_level == "critical":
                    return (
                        f"Patient {patient_ref} shows very high probability "
                        f"({prob_pct:.1f}%) of diabetes based on DTMH multimodal analysis. "
                        "Immediate clinical evaluation and diagnostic confirmation are strongly recommended."
                    )
                elif risk_level == "high":
                    return (
                        f"Patient {patient_ref} shows high probability "
                        f"({prob_pct:.1f}%) of diabetes. Confirmatory laboratory testing "
                        "with HbA1c and fasting glucose is recommended."
                    )
                elif risk_level == "moderate":
                    return (
                        f"Patient {patient_ref} shows moderate probability "
                        f"({prob_pct:.1f}%) of diabetes. Further evaluation with "
                        "laboratory testing is recommended."
                    )
                else:
                    return (
                        f"Patient {patient_ref} shows low probability "
                        f"({prob_pct:.1f}%) of diabetes based on current data. "
                        "Continue routine monitoring as clinically appropriate."
                    )

        elif task_type == "risk_assessment":
            return (
                f"Patient {patient_ref} has {risk_level} risk for diabetes-related "
                "complications based on DTMH risk prediction model. "
                "See recommendations for appropriate management and monitoring."
            )

        elif task_type == "complication_prediction":
            organ_states = model_outputs.get("organ_states", {})
            if organ_states:
                high_risk_organs = [
                    organ for organ, state in organ_states.items()
                    if isinstance(state, dict) and state.get("state") in ["high_probability", "very_high_probability"]
                ]
                if high_risk_organs:
                    organs_str = ", ".join(high_risk_organs)
                    return (
                        f"Patient {patient_ref} shows {risk_level} risk for complications "
                        f"affecting: {organs_str}. Specialist evaluation and enhanced "
                        "monitoring are recommended."
                    )

            return (
                f"Patient {patient_ref} has {risk_level} risk for diabetes complications "
                "based on DTMH prediction model."
            )

        # Default conclusion
        return (
            f"DTMH analysis for patient {patient_ref} indicates {risk_level} risk level. "
            "See detailed recommendations below."
        )

    def _extract_uncertainty(self, dtmh_response: dict[str, Any]) -> dict[str, Any]:
        """Extract uncertainty information from DTMH response."""
        uncertainty = dtmh_response.get("uncertainty", {})

        if not uncertainty or not isinstance(uncertainty, dict):
            uncertainty = {
                "level": "moderate",
                "note": "Model-based predictions require clinical validation",
            }

        return uncertainty

    def _extract_limitations(self, dtmh_response: dict[str, Any]) -> list[str]:
        """Extract data limitations and warnings from DTMH response."""
        limitations = []

        # Extract warnings
        warnings = dtmh_response.get("warnings", [])
        if isinstance(warnings, list):
            limitations.extend(warnings)

        # Check for data quality flags
        if "data_quality_flags" in dtmh_response:
            flags = dtmh_response["data_quality_flags"]
            if isinstance(flags, list) and flags:
                limitations.append(f"Data quality issues detected: {', '.join(flags)}")

        return limitations

    def _generate_recommendations(
        self,
        task_type: str,
        risk_level: str,
        model_outputs: dict[str, Any],
    ) -> list[str]:
        """Generate clinical recommendations based on risk level."""
        # Get base recommendations for task type and risk level
        task_recommendations = self.RECOMMENDATIONS.get(
            task_type,
            self.RECOMMENDATIONS["screening"],
        )

        recommendations = task_recommendations.get(
            risk_level,
            ["Clinical evaluation recommended based on model predictions"],
        )

        # Add organ-specific recommendations if available
        organ_states = model_outputs.get("organ_states", {})
        if organ_states and isinstance(organ_states, dict):
            for organ, state in organ_states.items():
                if isinstance(state, dict):
                    organ_risk = state.get("state", "")
                    if "high" in organ_risk.lower():
                        recommendations.append(
                            f"Specialist evaluation for {organ} complications"
                        )

        return recommendations
