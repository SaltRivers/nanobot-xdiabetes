"""Local patient-case storage for the X-Diabetes MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xdiabetes.x_diabetes.constants import DEFAULT_CASE_ID
from xdiabetes.x_diabetes.errors import PatientCaseNotFoundError
from xdiabetes.x_diabetes.schemas import PatientCase, PatientContext


class PatientStore:
    """Read structured patient cases from the workspace."""

    def __init__(self, cases_dir: Path, default_patient_id: str = DEFAULT_CASE_ID):
        self._cases_dir = cases_dir
        self._default_patient_id = default_patient_id
        self._cases_dir.mkdir(parents=True, exist_ok=True)

    @property
    def default_patient_id(self) -> str:
        return self._default_patient_id

    def list_cases(self) -> list[str]:
        """Return all available JSON case identifiers in the cases directory."""
        return sorted(path.stem for path in self._cases_dir.glob("*.json"))

    def load_case(self, patient_id: str | None = None, case_file: str | None = None) -> PatientCase:
        """Load a patient case by ID or explicit path.

        Exactly one of ``patient_id`` or ``case_file`` is preferred. If neither
        is supplied, the default demo case is loaded.
        """

        path = self._resolve_case_path(patient_id=patient_id, case_file=case_file)
        if not path.exists():
            raise PatientCaseNotFoundError(
                f"Patient case not found: {path}. Available cases: {', '.join(self.list_cases()) or '(none)'}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PatientCaseNotFoundError(f"Patient case file is not valid JSON: {path}") from exc

        case = PatientCase.model_validate(payload)
        if not case.patient_id:
            raise PatientCaseNotFoundError(f"Patient case file does not contain a patient_id: {path}")
        return case

    def build_context(self, patient: PatientCase) -> PatientContext:
        """Build a concise standardized patient context for the agent."""
        structured = patient.model_dump(mode="python")
        available_modalities = []
        missing_modalities = []
        modality_map: dict[str, Any] = {
            "labs": patient.labs,
            "vitals": patient.vitals,
            "cgm": patient.cgm,
            "imaging": patient.imaging,
            "medications": patient.medications,
            "history": patient.history,
        }
        for name, value in modality_map.items():
            has_value = bool(value)
            (available_modalities if has_value else missing_modalities).append(name)

        age = patient.demographics.get("age", "unknown")
        sex = patient.demographics.get("sex", "unknown")
        bmi = patient.demographics.get("bmi", "unknown")
        hba1c = patient.labs.get("hba1c", "unknown")
        fpg = patient.labs.get("fpg_mmol_l", "unknown")
        summary = (
            f"Patient {patient.patient_id}: age={age}, sex={sex}, bmi={bmi}, "
            f"HbA1c={hba1c}, FPG={fpg}, complications={patient.complications or 'none documented'}."
        )
        return PatientContext(
            patient_id=patient.patient_id,
            summary=summary,
            available_modalities=available_modalities,
            missing_modalities=missing_modalities,
            data_quality_flags=patient.data_quality_flags,
            structured_data=structured,
        )

    def _resolve_case_path(self, patient_id: str | None, case_file: str | None) -> Path:
        if case_file:
            return Path(case_file).expanduser()
        selected_id = patient_id or self._default_patient_id
        return self._cases_dir / f"{selected_id}.json"
