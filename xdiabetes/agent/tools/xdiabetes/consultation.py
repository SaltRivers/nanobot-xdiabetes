"""Primary consultation tool for the X-Diabetes MVP."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.schemas import ConsultationResult, DTMHRequest
from xdiabetes.x_diabetes.services import (
    KnowledgeRouter,
    PatientMemoryBuilder,
    PatientMemoryStore,
    PatientStore,
    ReportBuilder,
    SafetyEngine,
)


class XDiabetesConsultationTool(Tool):
    """Primary one-shot tool for doctor or patient consultation workflows."""

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
        return "xdiabetes_consultation"

    @property
    def description(self) -> str:
        return (
            "Primary X-Diabetes entrypoint. Use this first for a runnable, end-to-end diabetes consultation that "
            "loads the patient case, merges longitudinal memory, runs DTMH, retrieves evidence, applies safety "
            "checks, and writes a report."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient case identifier. Defaults to the demo case."},
                "case_file": {"type": "string", "description": "Optional explicit case JSON path."},
                "clinical_question": {"type": "string", "description": "Clinical question to answer."},
                "task": {
                    "type": "string",
                    "description": "Diabetes workflow type.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
                "audience": {
                    "type": "string",
                    "description": "Target audience. Defaults to the configured X-Diabetes mode.",
                    "enum": ["doctor", "patient"],
                },
                "save_report": {"type": "boolean", "description": "Whether to persist the generated report."},
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
        **_: Any,
    ) -> str:
        patient = self._patient_store.load_case(patient_id=patient_id, case_file=case_file)
        resolved_audience = audience or self._default_mode
        patient_context = self._patient_store.build_context(patient)
        if self._patient_memory_builder is not None:
            patient_context = self._patient_memory_builder.build_context(
                patient,
                patient_context,
                task=task,
                clinical_question=clinical_question,
            )
        search_query = f"{task} diabetes {clinical_question} {patient_context.summary}".strip()

        dtmh_result = self._dtmh_adapter.analyze(
            DTMHRequest(
                patient=patient,
                task=task,
                clinical_question=clinical_question,
                audience=resolved_audience,
            )
        )
        evidence_result = self._knowledge_router.search(
            query=search_query,
            patient_id=patient.patient_id,
            task=task,
            audience=resolved_audience,
        )
        evidence = evidence_result.hits
        safety = self._safety_engine.evaluate(patient, dtmh_result)
        report = self._report_builder.build_consultation_report(
            patient_context=patient_context,
            clinical_question=clinical_question,
            task=task,
            audience=resolved_audience,
            dtmh_result=dtmh_result,
            evidence=evidence,
            knowledge_metadata=evidence_result.metadata,
            safety=safety,
            save_report=save_report,
        )
        if self._patient_memory_store is not None:
            self._patient_memory_store.persist_consultation_artifacts(
                patient=patient,
                patient_context=patient_context,
                task=task,
                audience=resolved_audience,
                clinical_question=clinical_question,
                report=report,
                dtmh_result=dtmh_result,
                safety=safety,
                evidence=evidence,
                knowledge_metadata=evidence_result.metadata,
            )
        result = ConsultationResult(
            patient_context=patient_context,
            dtmh_result=dtmh_result,
            evidence=evidence,
            knowledge_metadata=evidence_result.metadata,
            safety=safety,
            report=report,
        )

        evidence_lines = [f"- {item.title}: {item.summary}" for item in evidence] or [
            "- No evidence matched or the configured RAG backend was unavailable."
        ]
        safety_lines = [
            f"- [{flag.severity.upper()}] {flag.code}: {flag.message}" for flag in safety.flags
        ] or ["- No rule-based flags."]
        report_hint = f"Saved report: {report.saved_path}" if report.saved_path else "Report was not saved."
        return "\n".join(
            [
                "# X-Diabetes Consultation Result",
                "",
                f"- Patient: {patient_context.patient_id}",
                f"- Task: {task}",
                f"- Audience: {resolved_audience}",
                f"- DTMH backend: {dtmh_result.backend}",
                "",
                "## Patient Context",
                patient_context.summary,
                "",
                "## DTMH Summary",
                dtmh_result.summary,
                "",
                "## Evidence",
                *evidence_lines,
                "",
                "## Knowledge Retrieval",
                f"- Requested backend: {evidence_result.metadata.backend_requested}",
                f"- Used backend: {evidence_result.metadata.backend_used}",
                f"- Status: {evidence_result.metadata.status}",
                f"- Result count: {evidence_result.metadata.result_count}",
                *(
                    [f"- Warning: {evidence_result.metadata.warning}"]
                    if evidence_result.metadata.warning
                    else []
                ),
                "",
                "## Safety Gate",
                f"Overall status: {safety.overall_status}",
                *safety_lines,
                "",
                "## Report",
                report_hint,
                "",
                "## Structured Result Snapshot",
                result.model_dump_json(indent=2),
            ]
        )
