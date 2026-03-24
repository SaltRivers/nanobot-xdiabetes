"""Safety check tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.schemas import DTMHRequest, DTMHResult
from xdiabetes.x_diabetes.services import PatientStore, SafetyEngine

from .common import dump_json, load_model_json


class XDiabetesSafetyCheckTool(Tool):
    """Evaluate deterministic safety rules for a patient case."""

    def __init__(
        self,
        *,
        patient_store: PatientStore,
        dtmh_adapter: DTMHAdapter,
        safety_engine: SafetyEngine,
    ):
        self._patient_store = patient_store
        self._dtmh_adapter = dtmh_adapter
        self._safety_engine = safety_engine

    @property
    def name(self) -> str:
        return "xdiabetes_safety_check"

    @property
    def description(self) -> str:
        return (
            "Run the X-Diabetes safety gate. Use this before presenting recommendations, especially when a case "
            "suggests poor control, renal impairment, pregnancy, or other high-risk signals."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient case identifier."},
                "case_file": {"type": "string", "description": "Optional explicit case JSON path."},
                "dtmh_json": {
                    "type": "string",
                    "description": "Optional JSON string produced by xdiabetes_dtmh. If omitted, the tool will compute a fresh DTMH result.",
                },
                "clinical_question": {"type": "string", "description": "Optional question passed to the fallback DTMH call."},
                "task": {
                    "type": "string",
                    "description": "Fallback DTMH task type when dtmh_json is omitted.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
            },
        }

    async def execute(
        self,
        patient_id: str | None = None,
        case_file: str | None = None,
        dtmh_json: str = "",
        clinical_question: str = "",
        task: str = "general",
        **_: Any,
    ) -> str:
        case = self._patient_store.load_case(patient_id=patient_id, case_file=case_file)
        dtmh_result = (
            load_model_json(dtmh_json, DTMHResult)
            if dtmh_json.strip()
            else self._dtmh_adapter.analyze(
                DTMHRequest(patient=case, task=task, clinical_question=clinical_question)
            )
        )
        assessment = self._safety_engine.evaluate(case, dtmh_result)
        return dump_json(assessment.model_dump(mode="json"))
