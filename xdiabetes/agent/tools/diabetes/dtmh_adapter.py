"""DTMH adapter tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from loguru import logger

from xdiabetes.agent.tools.base import Tool
from xdiabetes.clinical.adapters.base import DTMHAdapter
from xdiabetes.clinical.schemas import DTMHRequest, PatientCase
from xdiabetes.clinical.services import PatientStore

from .common import dump_json


class XDiabetesDTMHTool(Tool):
    """Run the configured DTMH adapter — the primary tool for diabetes inference.

    Supports two modes:

    1. **Direct CSV prediction** (preferred): provide ``cohort_dir`` and
       ``patient_id`` to call the remote DTMH HTTP service directly via
       ``/predict_csv``. No local patient case file is needed.

    2. **Local case-based**: provide ``patient_id`` or ``case_file`` to load
       a structured patient case from the workspace and send it through the
       configured adapter.
    """

    def __init__(self, *, patient_store: PatientStore, dtmh_adapter: DTMHAdapter):
        self._patient_store = patient_store
        self._dtmh_adapter = dtmh_adapter

    @property
    def name(self) -> str:
        return "xdiabetes_dtmh"

    @property
    def description(self) -> str:
        return (
            "Run the configured DTMH backend for diabetes analysis. "
            "For direct inference, provide cohort_dir and patient_id to call the "
            "remote DTMH HTTP service (e.g. /predict_csv). No local deep-learning "
            "libraries are needed. Alternatively, provide a local case file."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cohort_dir": {
                    "type": "string",
                    "description": "Path to the cohort dataset directory on the DTMH server (e.g. 'Dataset/private_fundus').",
                },
                "patient_id": {
                    "type": "integer",
                    "description": "Patient identifier. For CSV prediction this is typically an integer index.",
                },
                "case_file": {"type": "string", "description": "Optional explicit local case JSON path."},
                "clinical_question": {"type": "string", "description": "Clinical question to guide the analysis."},
                "task": {
                    "type": "string",
                    "description": "Analysis task type.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
                "audience": {
                    "type": "string",
                    "description": "Audience for downstream interpretation.",
                    "enum": ["doctor", "patient"],
                },
                "checkpoint_path": {
                    "type": "string",
                    "description": "Override the DTMH checkpoint path for this call.",
                },
                "config_path": {
                    "type": "string",
                    "description": "Override the DTMH config path for this call.",
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format: logits, probabilities, or binary.",
                    "enum": ["logits", "probabilities", "binary"],
                },
            },
        }

    async def execute(
        self,
        cohort_dir: str | None = None,
        patient_id: str | int | None = None,
        case_file: str | None = None,
        clinical_question: str = "",
        task: str = "general",
        audience: str = "doctor",
        checkpoint_path: str | None = None,
        config_path: str | None = None,
        output_format: str | None = None,
        **_: Any,
    ) -> str:
        logger.debug(
            "xdiabetes_dtmh execute: cohort_dir={} patient_id={} case_file={} task={} "
            "checkpoint_path={} config_path={} output_format={}",
            cohort_dir, patient_id, case_file, task,
            checkpoint_path, config_path, output_format,
        )

        # Apply per-call overrides to the adapter if provided
        if checkpoint_path and hasattr(self._dtmh_adapter, "_checkpoint_path"):
            self._dtmh_adapter._checkpoint_path = checkpoint_path
        if config_path and hasattr(self._dtmh_adapter, "_config_path"):
            self._dtmh_adapter._config_path = config_path
        if output_format and hasattr(self._dtmh_adapter, "_output_format"):
            self._dtmh_adapter._output_format = output_format

        if cohort_dir:
            # Direct CSV prediction mode — build a minimal PatientCase as carrier
            pid_str = str(patient_id) if patient_id is not None else "unknown"
            case = PatientCase(
                patient_id=pid_str,
                metadata={
                    "cohort_dir": cohort_dir,
                    "patient_id_csv": patient_id if patient_id is not None else pid_str,
                },
            )
        else:
            # Local case-based mode
            pid_str = str(patient_id) if patient_id is not None else None
            case = self._patient_store.load_case(patient_id=pid_str, case_file=case_file)

        result = self._dtmh_adapter.analyze(
            DTMHRequest(
                patient=case,
                task=task,
                clinical_question=clinical_question,
                audience=audience,
            )
        )
        logger.debug(
            "xdiabetes_dtmh result: patient_id={} backend={} summary={}",
            result.patient_id,
            result.backend,
            (result.summary or "")[:200],
        )
        return dump_json(result.model_dump(mode="json"))
