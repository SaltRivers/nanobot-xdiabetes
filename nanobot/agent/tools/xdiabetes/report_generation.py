"""Report generation tool for X-Diabetes."""

from __future__ import annotations

import json
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.x_diabetes.adapters.base import DTMHAdapter
from nanobot.x_diabetes.schemas import (
    DTMHRequest,
    DTMHResult,
    KnowledgeHit,
    KnowledgeRetrievalMetadata,
    SafetyAssessment,
)
from nanobot.x_diabetes.services import (
    KnowledgeRouter,
    PatientMemoryBuilder,
    PatientMemoryStore,
    PatientStore,
    ReportBuilder,
    SafetyEngine,
)

from .common import dump_json, load_json_list, load_model_json


class XDiabetesReportGenerationTool(Tool):
    """Build a persisted report for a patient case."""

    def __init__(
        self,
        *,
        patient_store: PatientStore,
        patient_memory_builder: PatientMemoryBuilder | None,
        patient_memory_store: PatientMemoryStore | None,
        knowledge_router: KnowledgeRouter,
        dtmh_adapter: DTMHAdapter,
        safety_engine: SafetyEngine,
        report_builder: ReportBuilder,
        default_mode: str,
    ):
        self._patient_store = patient_store
        self._patient_memory_builder = patient_memory_builder
        self._patient_memory_store = patient_memory_store
        self._knowledge_router = knowledge_router
        self._dtmh_adapter = dtmh_adapter
        self._safety_engine = safety_engine
        self._report_builder = report_builder
        self._default_mode = default_mode

    @property
    def name(self) -> str:
        return "xdiabetes_generate_report"

    @property
    def description(self) -> str:
        return (
            "Generate and optionally save a doctor- or patient-facing X-Diabetes report. "
            "If you do not already have intermediate JSON from other tools, this tool can compute everything for you."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient case identifier."},
                "case_file": {"type": "string", "description": "Optional explicit case JSON path."},
                "clinical_question": {"type": "string", "description": "Clinical question to answer in the report."},
                "task": {
                    "type": "string",
                    "description": "Analysis task type.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
                "audience": {
                    "type": "string",
                    "description": "Report audience. Defaults to the configured X-Diabetes mode.",
                    "enum": ["doctor", "patient"],
                },
                "save_report": {"type": "boolean", "description": "Whether to save the generated report to the workspace."},
                "dtmh_json": {"type": "string", "description": "Optional JSON from xdiabetes_dtmh."},
                "safety_json": {"type": "string", "description": "Optional JSON from xdiabetes_safety_check."},
                "evidence_json": {"type": "string", "description": "Optional JSON list from xdiabetes_guideline_search."},
                "knowledge_metadata_json": {
                    "type": "string",
                    "description": "Optional retrieval metadata JSON from xdiabetes_guideline_search(include_metadata=true).",
                },
            },
        }

    async def execute(
        self,
        patient_id: str | None = None,
        case_file: str | None = None,
        clinical_question: str = "",
        task: str = "general",
        audience: str | None = None,
        save_report: bool = True,
        dtmh_json: str = "",
        safety_json: str = "",
        evidence_json: str = "",
        knowledge_metadata_json: str = "",
        **_: Any,
    ) -> str:
        case = self._patient_store.load_case(patient_id=patient_id, case_file=case_file)
        resolved_audience = audience or self._default_mode
        context = self._patient_store.build_context(case)
        if self._patient_memory_builder is not None:
            context = self._patient_memory_builder.build_context(
                case,
                context,
                task=task,
                clinical_question=clinical_question,
            )

        dtmh_result = (
            load_model_json(dtmh_json, DTMHResult)
            if dtmh_json.strip()
            else self._dtmh_adapter.analyze(
                DTMHRequest(
                    patient=case,
                    task=task,
                    clinical_question=clinical_question,
                    audience=resolved_audience,
                )
            )
        )

        knowledge_metadata = None
        if knowledge_metadata_json.strip():
            payload = json.loads(knowledge_metadata_json)
            if isinstance(payload, dict) and isinstance(payload.get("metadata"), dict):
                payload = payload["metadata"]
            knowledge_metadata = KnowledgeRetrievalMetadata.model_validate(payload)
        if evidence_json.strip():
            evidence = [KnowledgeHit.model_validate(item) for item in load_json_list(evidence_json)]
        else:
            search_query = f"{task} diabetes {clinical_question} {context.summary}".strip()
            evidence_result = self._knowledge_router.search(
                query=search_query,
                patient_id=case.patient_id,
                task=task,
                audience=resolved_audience,
            )
            evidence = evidence_result.hits
            knowledge_metadata = knowledge_metadata or evidence_result.metadata

        safety = (
            load_model_json(safety_json, SafetyAssessment)
            if safety_json.strip()
            else self._safety_engine.evaluate(case, dtmh_result)
        )
        knowledge_metadata = knowledge_metadata or KnowledgeRetrievalMetadata(
            backend_requested="unknown",
            backend_used="unknown",
            status="unknown",
            result_count=len(evidence),
        )

        artifact = self._report_builder.build_consultation_report(
            patient_context=context,
            clinical_question=clinical_question,
            task=task,
            audience=resolved_audience,
            dtmh_result=dtmh_result,
            evidence=evidence,
            knowledge_metadata=knowledge_metadata,
            safety=safety,
            save_report=save_report,
        )
        if self._patient_memory_store is not None:
            self._patient_memory_store.persist_consultation_artifacts(
                patient=case,
                patient_context=context,
                task=task,
                audience=resolved_audience,
                clinical_question=clinical_question,
                report=artifact,
                dtmh_result=dtmh_result,
                safety=safety,
                evidence=evidence,
                knowledge_metadata=knowledge_metadata,
            )
        return dump_json(artifact.model_dump(mode="json"))
