"""Patient data preparation and validation.

This module handles data quality assessment, standardization, and
preparation of DTMH-ready payloads.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from loguru import logger

from xdiabetes.clinical.foundation.schemas import (
    ClinicalTaskPlan,
    DataPreparationResult,
)
from xdiabetes.clinical.schemas import PatientCase


class DataManager:
    """Patient data preparation and validation engine.

    This class validates patient data completeness, standardizes clinical
    variables, and prepares DTMH-ready payloads with quality assessment.
    """

    # Required fields by modality
    MODALITY_REQUIRED_FIELDS = {
        "demographics": ["age", "sex"],
        "vitals": ["sbp", "dbp"],
        "labs": ["hba1c"],
        "imaging": [],  # Optional, depends on task
        "cgm": [],  # Optional, depends on task
        "medications": [],  # Optional, depends on task
        "history": [],  # Optional, depends on task
        "complications": [],  # Optional, depends on task
    }

    # Critical fields for diabetes screening
    SCREENING_CRITICAL_FIELDS = [
        "demographics.age",
        "demographics.sex",
        "labs.hba1c",
    ]

    def __init__(self):
        """Initialize the data manager."""
        pass

    async def prepare_data(
        self,
        task_plan: ClinicalTaskPlan,
        patient_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> DataPreparationResult:
        """Prepare and validate patient data for DTMH inference.

        Args:
            task_plan: Clinical task plan specifying required data
            patient_data: Raw patient data dictionary
            context: Optional context information

        Returns:
            DataPreparationResult with validation status and prepared payload
        """
        logger.debug(
            "Preparing data for patient={} task={}",
            task_plan.patient_reference,
            task_plan.task_type,
        )

        # Extract cohort_dir from query if present (for CSV mode)
        cohort_dir = self._extract_cohort_dir(task_plan.original_query)

        # If cohort_dir is present, use CSV mode (minimal validation)
        if cohort_dir:
            return await self._prepare_csv_mode(task_plan, cohort_dir, context)

        # Otherwise, prepare from patient_data (full validation)
        return await self._prepare_case_mode(task_plan, patient_data, context)

    async def _prepare_csv_mode(
        self,
        task_plan: ClinicalTaskPlan,
        cohort_dir: str,
        context: dict[str, Any] | None = None,
    ) -> DataPreparationResult:
        """Prepare data for CSV mode (cohort_dir + patient_id).

        In CSV mode, the DTMH service loads data directly from the cohort
        directory, so we only validate that the reference is present.
        """
        patient_id = task_plan.patient_reference

        # Validate patient_id is present
        if not patient_id:
            return DataPreparationResult(
                patient_id="unknown",
                available_modalities=[],
                missing_fields=["patient_id"],
                temporal_coverage={},
                dtmh_ready=False,
                payload_preview={},
                data_quality_flags=["missing_patient_id"],
            )

        # CSV mode is ready if both cohort_dir and patient_id are present
        dtmh_ready = bool(cohort_dir and patient_id)

        return DataPreparationResult(
            patient_id=patient_id,
            available_modalities=["cohort_csv"],
            missing_fields=[],
            temporal_coverage={},
            dtmh_ready=dtmh_ready,
            payload_preview={
                "cohort_dir": cohort_dir,
                "patient_id": patient_id,
                "mode": "csv",
            },
            data_quality_flags=[],
        )

    async def _prepare_case_mode(
        self,
        task_plan: ClinicalTaskPlan,
        patient_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> DataPreparationResult:
        """Prepare data from patient_data dictionary (full validation)."""
        patient_id = task_plan.patient_reference or "unknown"

        if not patient_data:
            return DataPreparationResult(
                patient_id=patient_id,
                available_modalities=[],
                missing_fields=task_plan.required_data,
                temporal_coverage={},
                dtmh_ready=False,
                payload_preview={},
                data_quality_flags=["no_patient_data_provided"],
            )

        # Check available modalities
        available_modalities = self._check_available_modalities(patient_data)

        # Check missing fields
        missing_fields = self._check_missing_fields(
            patient_data,
            task_plan.required_data,
        )

        # Assess temporal coverage
        temporal_coverage = self._assess_temporal_coverage(patient_data)

        # Generate data quality flags
        quality_flags = self._generate_quality_flags(
            patient_data,
            available_modalities,
            missing_fields,
            task_plan.task_type,
        )

        # Standardize patient data
        standardized_case = self._standardize_patient_case(
            patient_id,
            patient_data,
        )

        # Check if data is DTMH-ready
        dtmh_ready = self._is_dtmh_ready(
            available_modalities,
            missing_fields,
            quality_flags,
            task_plan.task_type,
        )

        # Prepare payload preview
        payload_preview = {
            "patient_id": patient_id,
            "mode": "case",
            "available_modalities": available_modalities,
            "case_preview": {
                "demographics": standardized_case.demographics,
                "vitals": standardized_case.vitals,
                "labs": standardized_case.labs,
            },
        }

        return DataPreparationResult(
            patient_id=patient_id,
            available_modalities=available_modalities,
            missing_fields=missing_fields,
            temporal_coverage=temporal_coverage,
            dtmh_ready=dtmh_ready,
            payload_preview=payload_preview,
            data_quality_flags=quality_flags,
        )

    def _extract_cohort_dir(self, query: str) -> str:
        """Extract cohort directory from query."""
        cohort_match = re.search(
            r"(?:in|from)\s+([\w/._-]+)",
            query,
            re.IGNORECASE,
        )
        return cohort_match.group(1) if cohort_match else ""

    def _check_available_modalities(
        self,
        patient_data: dict[str, Any],
    ) -> list[str]:
        """Check which data modalities are present."""
        available = []

        modality_keys = {
            "demographics": ["demographics", "demo", "patient_info"],
            "vitals": ["vitals", "vital_signs"],
            "labs": ["labs", "laboratory", "lab_results"],
            "imaging": ["imaging", "images", "fundus", "retina"],
            "cgm": ["cgm", "glucose_monitoring", "continuous_glucose"],
            "medications": ["medications", "meds", "drugs"],
            "history": ["history", "medical_history", "past_history"],
            "complications": ["complications", "comorbidities"],
            "timeline": ["timeline", "events", "longitudinal"],
        }

        for modality, keys in modality_keys.items():
            for key in keys:
                if key in patient_data and patient_data[key]:
                    available.append(modality)
                    break

        return available

    def _check_missing_fields(
        self,
        patient_data: dict[str, Any],
        required_modalities: list[str],
    ) -> list[str]:
        """Check for missing required fields."""
        missing = []

        for modality in required_modalities:
            required_fields = self.MODALITY_REQUIRED_FIELDS.get(modality, [])

            # Get modality data
            modality_data = patient_data.get(modality, {})
            if not isinstance(modality_data, dict):
                if required_fields:
                    missing.extend([f"{modality}.{field}" for field in required_fields])
                continue

            # Check required fields
            for field in required_fields:
                if field not in modality_data or modality_data[field] in (None, "", []):
                    missing.append(f"{modality}.{field}")

        return missing

    def _assess_temporal_coverage(
        self,
        patient_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess temporal coverage of patient data."""
        coverage = {
            "has_timeline": "timeline" in patient_data,
            "has_longitudinal_data": False,
            "time_span_days": 0,
            "data_points": 0,
        }

        # Check timeline
        timeline = patient_data.get("timeline", [])
        if isinstance(timeline, list) and timeline:
            coverage["has_longitudinal_data"] = True
            coverage["data_points"] = len(timeline)

            # Calculate time span if timestamps are present
            timestamps = []
            for event in timeline:
                if isinstance(event, dict) and "timestamp" in event:
                    try:
                        ts = event["timestamp"]
                        if isinstance(ts, str):
                            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        timestamps.append(ts)
                    except (ValueError, TypeError):
                        pass

            if len(timestamps) >= 2:
                time_span = max(timestamps) - min(timestamps)
                coverage["time_span_days"] = time_span.days

        return coverage

    def _generate_quality_flags(
        self,
        patient_data: dict[str, Any],
        available_modalities: list[str],
        missing_fields: list[str],
        task_type: str,
    ) -> list[str]:
        """Generate data quality flags."""
        flags = []

        # Check for critical missing fields
        if task_type == "screening":
            for critical_field in self.SCREENING_CRITICAL_FIELDS:
                if critical_field in missing_fields:
                    flags.append(f"missing_critical_field_{critical_field}")

        # Check for missing modalities
        if "demographics" not in available_modalities:
            flags.append("missing_demographics")

        if task_type in ["screening", "risk_assessment"] and "labs" not in available_modalities:
            flags.append("missing_labs")

        # Check for data quality issues
        demographics = patient_data.get("demographics", {})
        if isinstance(demographics, dict):
            age = demographics.get("age")
            if age is not None:
                try:
                    age_val = float(age)
                    if age_val < 0 or age_val > 120:
                        flags.append("invalid_age_range")
                except (ValueError, TypeError):
                    flags.append("invalid_age_format")

        # Check for sparse data
        if len(available_modalities) < 3:
            flags.append("sparse_data")

        return flags

    def _standardize_patient_case(
        self,
        patient_id: str,
        patient_data: dict[str, Any],
    ) -> PatientCase:
        """Standardize patient data into PatientCase schema."""
        return PatientCase(
            patient_id=patient_id,
            demographics=patient_data.get("demographics", {}),
            vitals=patient_data.get("vitals", {}),
            labs=patient_data.get("labs", {}),
            cgm=patient_data.get("cgm", {}),
            imaging=patient_data.get("imaging", {}),
            medications=patient_data.get("medications", []),
            history=patient_data.get("history", {}),
            complications=patient_data.get("complications", []),
            notes=patient_data.get("notes", ""),
            timeline=patient_data.get("timeline", []),
            metadata=patient_data.get("metadata", {}),
        )

    def _is_dtmh_ready(
        self,
        available_modalities: list[str],
        missing_fields: list[str],
        quality_flags: list[str],
        task_type: str,
    ) -> bool:
        """Determine if data is ready for DTMH inference."""
        # Check for critical missing fields
        if task_type == "screening":
            for critical_field in self.SCREENING_CRITICAL_FIELDS:
                if critical_field in missing_fields:
                    return False

        # Check for blocking quality flags
        blocking_flags = [
            "missing_demographics",
            "invalid_age_format",
        ]

        for flag in blocking_flags:
            if flag in quality_flags:
                return False

        # Require minimum modalities
        if len(available_modalities) < 1:
            return False

        return True
