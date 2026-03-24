"""Patient context tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.services import PatientMemoryBuilder, PatientStore

from .common import dump_json


class XDiabetesPatientContextTool(Tool):
    """Load a patient case and normalize it for downstream analysis."""

    def __init__(
        self,
        *,
        patient_store: PatientStore,
        patient_memory_builder: PatientMemoryBuilder | None = None,
    ):
        self._patient_store = patient_store
        self._patient_memory_builder = patient_memory_builder

    @property
    def name(self) -> str:
        return "xdiabetes_patient_context"

    @property
    def description(self) -> str:
        return (
            "Load a structured diabetes patient case from the X-Diabetes workspace and return a "
            "normalized patient context. Use this when you need the raw case before other analysis tools."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient case identifier. Defaults to the configured demo case.",
                },
                "case_file": {
                    "type": "string",
                    "description": "Optional explicit JSON path. Use this when the case is outside the default cases directory.",
                },
                "task": {
                    "type": "string",
                    "description": "Optional workflow type used to select relevant longitudinal memory slices.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
                "clinical_question": {
                    "type": "string",
                    "description": "Optional current clinical question to annotate the longitudinal context.",
                },
            },
        }

    async def execute(
        self,
        patient_id: str | None = None,
        case_file: str | None = None,
        task: str = "general",
        clinical_question: str = "",
        **_: Any,
    ) -> str:
        case = self._patient_store.load_case(patient_id=patient_id, case_file=case_file)
        context = self._patient_store.build_context(case)
        if self._patient_memory_builder is not None:
            context = self._patient_memory_builder.build_context(
                case,
                context,
                task=task,
                clinical_question=clinical_question,
            )
        return dump_json(context.model_dump(mode="json"))
