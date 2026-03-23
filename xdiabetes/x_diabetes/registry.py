"""Tool registration entrypoint for the X-Diabetes profile."""

from __future__ import annotations

from pathlib import Path

from xdiabetes.agent.tools.registry import ToolRegistry
from xdiabetes.agent.tools.xdiabetes import (
    XDiabetesConsultationTool,
    XDiabetesDTMHTool,
    XDiabetesGuidelineSearchTool,
    XDiabetesPatientContextTool,
    XDiabetesPatientMemoryTool,
    XDiabetesReportGenerationTool,
    XDiabetesSafetyCheckTool,
)
from xdiabetes.config.schema import XDiabetesConfig
from xdiabetes.x_diabetes.adapters import build_dtmh_adapter
from xdiabetes.x_diabetes.services import (
    KnowledgeRouter,
    KnowledgeStore,
    PatientMemoryBuilder,
    PatientMemoryStore,
    PatientStore,
    RAGAPIClient,
    ReportBuilder,
    SafetyEngine,
)


def _resolve_relative_path(workspace: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else workspace / candidate


def register_x_diabetes_tools(
    registry: ToolRegistry,
    *,
    workspace: Path,
    config: XDiabetesConfig,
) -> None:
    """Register all X-Diabetes tools on a tool registry."""

    cases_dir = _resolve_relative_path(workspace, config.cases_dir)
    knowledge_dir = _resolve_relative_path(workspace, config.knowledge_dir)
    reports_dir = _resolve_relative_path(workspace, config.reports_dir)
    rules_path = _resolve_relative_path(workspace, config.rules_path)
    patient_memory_dir = _resolve_relative_path(workspace, config.memory.patient_memory_dir)

    patient_store = PatientStore(cases_dir, default_patient_id=config.default_patient_id)
    patient_memory_store = None
    patient_memory_builder = None
    if config.memory.enabled:
        patient_memory_store = PatientMemoryStore(
            patient_memory_dir,
            summary_filename=config.memory.summary_filename,
            write_encounter=config.memory.write_encounter,
            write_risk_assessment=config.memory.write_risk_assessment,
            write_report_index=config.memory.write_report_index,
        )
        patient_memory_builder = PatientMemoryBuilder(
            patient_memory_store,
            timeline_max_read=config.memory.timeline_max_read,
        )
    knowledge_store = KnowledgeStore(knowledge_dir)
    api_client = None
    if config.rag.backend in {"api", "hybrid"} and config.rag.api_base_url:
        api_client = RAGAPIClient(
            base_url=config.rag.api_base_url,
            search_endpoint=config.rag.search_endpoint,
            health_endpoint=config.rag.health_endpoint,
            timeout_s=config.rag.timeout_s,
            headers=config.rag.headers,
        )
    knowledge_router = KnowledgeRouter(
        backend=config.rag.backend,
        local_store=knowledge_store,
        api_client=api_client,
        ignore_failure=config.rag.ignore_failure,
        fallback_to_local=config.rag.fallback_to_local,
        default_top_k=config.rag.top_k,
    )
    safety_engine = SafetyEngine(rules_path)
    report_builder = ReportBuilder(reports_dir)
    dtmh_adapter = build_dtmh_adapter(config)

    registry.register(
        XDiabetesPatientContextTool(
            patient_store=patient_store,
            patient_memory_builder=patient_memory_builder,
        )
    )
    if patient_memory_store is not None:
        registry.register(
            XDiabetesPatientMemoryTool(
                patient_memory_store=patient_memory_store,
                timeline_max_read=config.memory.timeline_max_read,
            )
        )
    registry.register(XDiabetesGuidelineSearchTool(knowledge_router=knowledge_router))
    registry.register(XDiabetesDTMHTool(patient_store=patient_store, dtmh_adapter=dtmh_adapter))
    registry.register(
        XDiabetesSafetyCheckTool(
            patient_store=patient_store,
            dtmh_adapter=dtmh_adapter,
            safety_engine=safety_engine,
        )
    )
    registry.register(
        XDiabetesReportGenerationTool(
            patient_store=patient_store,
            patient_memory_builder=patient_memory_builder,
            patient_memory_store=patient_memory_store,
            knowledge_router=knowledge_router,
            dtmh_adapter=dtmh_adapter,
            safety_engine=safety_engine,
            report_builder=report_builder,
            default_mode=config.mode,
        )
    )
    registry.register(
        XDiabetesConsultationTool(
            patient_store=patient_store,
            patient_memory_builder=patient_memory_builder,
            patient_memory_store=patient_memory_store,
            knowledge_router=knowledge_router,
            dtmh_adapter=dtmh_adapter,
            safety_engine=safety_engine,
            report_builder=report_builder,
            default_mode=config.mode,
        )
    )
