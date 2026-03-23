"""DTMH adapter tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.schemas import DTMHRequest
from xdiabetes.x_diabetes.services import PatientStore

from .common import dump_json


class XDiabetesDTMHTool(Tool):
    """Run the configured DTMH adapter over a patient case."""

    def __init__(self, *, patient_store: PatientStore, dtmh_adapter: DTMHAdapter):
        self._patient_store = patient_store
        self._dtmh_adapter = dtmh_adapter

    @property
    def name(self) -> str:
        return "xdiabetes_dtmh"

    @property
    def description(self) -> str:
        return (
            "Run the configured DTMH backend for a patient case. In the current repository state this usually "
            "uses the mock backend because the real DTMH is still training."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient case identifier."},
                "case_file": {"type": "string", "description": "Optional explicit case JSON path."},
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
            },
        }

    async def execute(
        self,
        patient_id: str | None = None,
        case_file: str | None = None,
        clinical_question: str = "",
        task: str = "general",
        audience: str = "doctor",
        **_: Any,
    ) -> str:
        case = self._patient_store.load_case(patient_id=patient_id, case_file=case_file)
        result = self._dtmh_adapter.analyze(
            DTMHRequest(
                patient=case,
                task=task,
                clinical_question=clinical_question,
                audience=audience,
            )
        )
        return dump_json(result.model_dump(mode="json"))
