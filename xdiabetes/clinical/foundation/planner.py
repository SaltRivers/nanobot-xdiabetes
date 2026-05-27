"""Query decomposition and guideline-based planning.

This module implements the first phase of the Foundation Agent workflow:
understanding the user's clinical query and planning the appropriate workflow.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from xdiabetes.clinical.foundation.schemas import ClinicalTaskPlan, GuidelinePlan


class ClinicalPlanner:
    """Query decomposition and guideline-based planning engine.

    This class transforms natural language clinical queries into structured
    task plans with guideline-grounded workflow steps.
    """

    # Task type patterns for query classification
    TASK_PATTERNS = {
        "screening": [
            r"\b(screen|check|test|detect|diagnose|has diabetes|have diabetes)\b",
            r"\b(diabetes status|diabetic)\b",
        ],
        "risk_assessment": [
            r"\b(risk|probability|likelihood|chance|predict)\b",
            r"\b(complication|progression|outcome)\b",
        ],
        "subtyping": [
            r"\b(type|subtype|classify|classification)\b",
            r"\b(type 1|type 2|t1d|t2d|gestational)\b",
        ],
        "complication_prediction": [
            r"\b(complication|retinopathy|neuropathy|nephropathy|cardiovascular)\b",
            r"\b(organ damage|end-organ|microvascular|macrovascular)\b",
        ],
        "trajectory_analysis": [
            r"\b(trajectory|progression|trend|over time|longitudinal)\b",
            r"\b(history|timeline|evolution|course)\b",
        ],
        "treatment_planning": [
            r"\b(treat|treatment|therapy|manage|management)\b",
            r"\b(medication|drug|insulin|metformin)\b",
        ],
        "medication_recommendation": [
            r"\b(recommend|suggest|prescribe|medication|drug)\b",
            r"\b(what medication|which drug|treatment option)\b",
        ],
    }

    # DTMH capability mapping
    CAPABILITY_MAP = {
        "screening": "diabetes_screening",
        "risk_assessment": "complication_prediction",
        "subtyping": "subtype_classification",
        "complication_prediction": "complication_prediction",
        "trajectory_analysis": "trajectory_prediction",
        "treatment_planning": "treatment_response",
        "medication_recommendation": "medication_type",
    }

    # Guideline references by task type
    GUIDELINE_REFERENCES = {
        "screening": [
            "ADA Standards of Medical Care in Diabetes",
            "WHO Diabetes Diagnostic Criteria",
            "USPSTF Diabetes Screening Guidelines",
        ],
        "risk_assessment": [
            "ADA Standards of Medical Care in Diabetes",
            "UKPDS Risk Engine Guidelines",
            "ACC/AHA Cardiovascular Risk Assessment",
        ],
        "subtyping": [
            "ADA Classification of Diabetes",
            "WHO Diabetes Classification",
        ],
        "complication_prediction": [
            "ADA Microvascular Complications Guidelines",
            "KDIGO Diabetic Kidney Disease Guidelines",
            "AAO Diabetic Retinopathy Guidelines",
        ],
        "trajectory_analysis": [
            "ADA Standards of Medical Care in Diabetes",
            "Diabetes Control and Complications Trial (DCCT)",
        ],
        "treatment_planning": [
            "ADA Pharmacologic Approaches to Glycemic Treatment",
            "AACE/ACE Diabetes Management Algorithm",
        ],
        "medication_recommendation": [
            "ADA Pharmacologic Approaches to Glycemic Treatment",
            "AACE/ACE Diabetes Management Algorithm",
            "NICE Type 2 Diabetes Management Guidelines",
        ],
    }

    def __init__(self):
        """Initialize the clinical planner."""
        pass

    async def decompose_query(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ClinicalTaskPlan:
        """Decompose user query into structured clinical task.

        Args:
            query: User's natural language query
            context: Optional context information

        Returns:
            ClinicalTaskPlan with structured task decomposition
        """
        logger.debug("Decomposing query: {}", query[:100])

        # Extract patient reference
        patient_ref = self._extract_patient_reference(query)

        # Determine task type
        task_type = self._classify_task_type(query)

        # Extract data references (cohort_dir, file paths, etc.)
        data_refs = self._extract_data_references(query)

        # Determine required data modalities
        required_data = self._determine_required_data(task_type, query)

        # Map to DTMH capability
        dtmh_capability = self.CAPABILITY_MAP.get(task_type, "diabetes_screening")

        # Determine audience
        audience = self._determine_audience(query, context)

        # Decompose into sub-tasks if complex
        sub_tasks = self._decompose_sub_tasks(query, task_type)

        task_plan = ClinicalTaskPlan(
            original_query=query,
            task_type=task_type,
            audience=audience,
            patient_reference=patient_ref,
            sub_tasks=sub_tasks,
            required_data=required_data,
            required_dtmh_capability=dtmh_capability,
        )

        logger.debug(
            "Query decomposed: task_type={} patient={} capability={}",
            task_type,
            patient_ref,
            dtmh_capability,
        )

        return task_plan

    async def plan_workflow(
        self,
        task_plan: ClinicalTaskPlan,
        context: dict[str, Any] | None = None,
    ) -> GuidelinePlan:
        """Create guideline-based workflow plan.

        Args:
            task_plan: Structured clinical task plan
            context: Optional context information

        Returns:
            GuidelinePlan with clinical workflow steps
        """
        logger.debug("Planning workflow for task_type={}", task_plan.task_type)

        # Define clinical workflow steps based on task type
        clinical_steps = self._define_clinical_steps(task_plan)

        # Get relevant guideline references
        guideline_basis = self.GUIDELINE_REFERENCES.get(
            task_plan.task_type,
            ["ADA Standards of Medical Care in Diabetes"],
        )

        # Determine required evidence
        required_evidence = self._determine_required_evidence(task_plan)

        # Specify safety checks
        required_safety_checks = self._determine_safety_checks(task_plan)

        # Set expected DTMH outputs
        expected_outputs = self._determine_expected_outputs(task_plan)

        guideline_plan = GuidelinePlan(
            clinical_steps=clinical_steps,
            guideline_basis=guideline_basis,
            required_evidence=required_evidence,
            required_safety_checks=required_safety_checks,
            expected_dtmh_outputs=expected_outputs,
        )

        logger.debug(
            "Workflow planned: {} steps, {} guidelines",
            len(clinical_steps),
            len(guideline_basis),
        )

        return guideline_plan

    def _extract_patient_reference(self, query: str) -> str:
        """Extract patient identifier from query."""
        # Pattern: "patient 4", "patient ID 123", "pt 4", etc.
        patterns = [
            r"patient\s+(?:id\s+)?(\d+)",
            r"pt\.?\s+(\d+)",
            r"patient\s+([A-Za-z0-9_-]+)",
            r"for\s+patient\s+([A-Za-z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)

        return ""

    def _classify_task_type(self, query: str) -> str:
        """Classify the clinical task type from query."""
        query_lower = query.lower()

        # Score each task type based on pattern matches
        scores = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > 0:
                scores[task_type] = score

        # Return task type with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        # Default to screening
        return "screening"

    def _extract_data_references(self, query: str) -> dict[str, str]:
        """Extract data references like cohort_dir, file paths."""
        refs = {}

        # Extract cohort directory
        cohort_match = re.search(
            r"(?:in|from)\s+([\w/._-]+(?:Dataset|dataset|data)[\w/._-]*)",
            query,
            re.IGNORECASE,
        )
        if cohort_match:
            refs["cohort_dir"] = cohort_match.group(1)

        # Extract file paths
        file_match = re.search(r"(?:file|path):\s*([^\s]+)", query, re.IGNORECASE)
        if file_match:
            refs["file_path"] = file_match.group(1)

        return refs

    def _determine_required_data(self, task_type: str, query: str) -> list[str]:
        """Determine required data modalities based on task type."""
        # Base modalities for all tasks
        base_modalities = ["demographics"]

        # Task-specific modalities
        task_modalities = {
            "screening": ["labs", "imaging", "vitals"],
            "risk_assessment": ["labs", "vitals", "history", "complications"],
            "subtyping": ["labs", "cgm", "history"],
            "complication_prediction": ["labs", "imaging", "vitals", "history"],
            "trajectory_analysis": ["labs", "cgm", "timeline"],
            "treatment_planning": ["labs", "medications", "history", "complications"],
            "medication_recommendation": ["labs", "medications", "history", "complications"],
        }

        modalities = base_modalities + task_modalities.get(task_type, [])

        # Add modalities mentioned in query
        if "fundus" in query.lower() or "retina" in query.lower():
            if "imaging" not in modalities:
                modalities.append("imaging")
        if "cgm" in query.lower() or "glucose monitor" in query.lower():
            if "cgm" not in modalities:
                modalities.append("cgm")

        return modalities

    def _determine_audience(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Determine target audience (doctor or patient)."""
        query_lower = query.lower()

        # Check for patient-facing indicators
        patient_indicators = [
            "explain to patient",
            "patient-friendly",
            "for patient",
            "layman",
            "simple terms",
        ]

        if any(indicator in query_lower for indicator in patient_indicators):
            return "patient"

        # Check context
        if context and context.get("audience") == "patient":
            return "patient"

        # Default to doctor
        return "doctor"

    def _decompose_sub_tasks(self, query: str, task_type: str) -> list[str]:
        """Decompose complex queries into sub-tasks."""
        sub_tasks = []

        # Check for multiple questions
        if " and " in query.lower() or ";" in query:
            # Complex query - decompose
            if task_type == "risk_assessment":
                sub_tasks = [
                    "Assess current diabetes status",
                    "Evaluate complication risk factors",
                    "Generate risk stratification",
                ]
            elif task_type == "treatment_planning":
                sub_tasks = [
                    "Review current treatment regimen",
                    "Assess treatment response",
                    "Recommend treatment adjustments",
                ]

        return sub_tasks

    def _define_clinical_steps(self, task_plan: ClinicalTaskPlan) -> list[str]:
        """Define clinical workflow steps based on task type."""
        task_type = task_plan.task_type

        # Common initial steps
        common_steps = [
            "Validate patient data availability and quality",
        ]

        # Task-specific workflow steps
        task_steps = {
            "screening": [
                "Load patient data from cohort",
                "Execute DTMH diabetes screening model",
                "Interpret diabetes probability",
                "Generate clinical screening report",
            ],
            "risk_assessment": [
                "Load patient clinical history",
                "Execute DTMH complication prediction model",
                "Stratify risk by organ system",
                "Generate risk assessment report",
            ],
            "subtyping": [
                "Load patient metabolic profile",
                "Execute DTMH subtype classification model",
                "Interpret diabetes subtype",
                "Generate classification report",
            ],
            "complication_prediction": [
                "Load patient longitudinal data",
                "Execute DTMH complication prediction model",
                "Assess organ-specific risk",
                "Generate complication risk report",
            ],
            "trajectory_analysis": [
                "Load patient timeline data",
                "Execute DTMH trajectory prediction model",
                "Analyze disease progression",
                "Generate trajectory report",
            ],
            "treatment_planning": [
                "Load patient treatment history",
                "Execute DTMH treatment response model",
                "Evaluate treatment options",
                "Generate treatment plan",
            ],
            "medication_recommendation": [
                "Load patient medication history",
                "Execute DTMH medication recommendation model",
                "Rank medication options",
                "Generate medication recommendation report",
            ],
        }

        steps = common_steps + task_steps.get(task_type, task_steps["screening"])

        return steps

    def _determine_required_evidence(self, task_plan: ClinicalTaskPlan) -> list[str]:
        """Determine required evidence types."""
        evidence_types = ["clinical_guidelines"]

        task_type = task_plan.task_type

        if task_type in ["screening", "risk_assessment"]:
            evidence_types.append("screening_criteria")

        if task_type in ["treatment_planning", "medication_recommendation"]:
            evidence_types.extend(["treatment_guidelines", "medication_safety"])

        if task_type == "complication_prediction":
            evidence_types.append("complication_criteria")

        return evidence_types

    def _determine_safety_checks(self, task_plan: ClinicalTaskPlan) -> list[str]:
        """Determine required safety checks."""
        safety_checks = [
            "data_quality_validation",
            "model_uncertainty_assessment",
        ]

        task_type = task_plan.task_type

        if task_type in ["treatment_planning", "medication_recommendation"]:
            safety_checks.extend([
                "contraindication_check",
                "drug_interaction_check",
            ])

        if task_plan.audience == "patient":
            safety_checks.append("patient_safety_language")

        return safety_checks

    def _determine_expected_outputs(self, task_plan: ClinicalTaskPlan) -> list[str]:
        """Determine expected DTMH output types."""
        task_type = task_plan.task_type

        output_map = {
            "screening": ["diabetes_probability"],
            "risk_assessment": ["risk_scores", "complication_probabilities"],
            "subtyping": ["subtype_classification", "subtype_probabilities"],
            "complication_prediction": ["organ_risk_scores", "complication_timeline"],
            "trajectory_analysis": ["trajectory_prediction", "progression_rate"],
            "treatment_planning": ["treatment_response_prediction"],
            "medication_recommendation": ["medication_ranking", "efficacy_prediction"],
        }

        return output_map.get(task_type, ["diabetes_probability"])
