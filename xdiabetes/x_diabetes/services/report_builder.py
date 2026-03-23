"""Report generation utilities for X-Diabetes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from xdiabetes.x_diabetes.constants import DEFAULT_REPORT_FILENAME_PREFIX
from xdiabetes.x_diabetes.schemas import (
    DTMHResult,
    KnowledgeHit,
    KnowledgeRetrievalMetadata,
    PatientContext,
    ReportArtifact,
    SafetyAssessment,
)


class ReportBuilder:
    """Build Markdown reports for doctor- and patient-facing workflows."""

    def __init__(self, reports_dir: Path):
        self._reports_dir = reports_dir
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def build_consultation_report(
        self,
        *,
        patient_context: PatientContext,
        clinical_question: str,
        task: str,
        audience: str,
        dtmh_result: DTMHResult,
        evidence: list[KnowledgeHit],
        knowledge_metadata: KnowledgeRetrievalMetadata | None,
        safety: SafetyAssessment,
        save_report: bool = True,
    ) -> ReportArtifact:
        """Build and optionally persist a Markdown report artifact."""
        next_step_lines = [f"- {item}" for item in dtmh_result.recommended_next_steps] or ["- None"]
        evidence_lines = []
        for hit in evidence:
            evidence_lines.append(
                f"- **{hit.title}** ({hit.source}, score={hit.score:.1f}) — {hit.summary}"
                + (f"\n  - Snippet: {hit.snippet}" if hit.snippet else "")
            )
        if not evidence_lines:
            evidence_lines = ["- No supporting evidence was returned by the configured knowledge backends."]

        safety_lines = [
            f"- [{flag.severity.upper()}] **{flag.code}** — {flag.message} Recommendation: {flag.recommendation}"
            for flag in safety.flags
        ] or ["- No rule-based safety flags were raised."]

        organ_lines = [
            f"- **{name}**: {payload.get('state', 'unknown')} (score={payload.get('score', 'n/a')})"
            for name, payload in dtmh_result.organ_states.items()
        ] or ["- No organ-state output returned."]

        knowledge_lines = ["- Retrieval metadata unavailable."]
        if knowledge_metadata is not None:
            knowledge_lines = [
                f"- **Requested backend**: {knowledge_metadata.backend_requested}",
                f"- **Used backend**: {knowledge_metadata.backend_used}",
                f"- **Status**: {knowledge_metadata.status}",
                f"- **Result count**: {knowledge_metadata.result_count}",
            ]
            if knowledge_metadata.warning:
                knowledge_lines.append(f"- **Warning**: {knowledge_metadata.warning}")

        longitudinal_lines = (
            [patient_context.longitudinal_summary]
            if patient_context.longitudinal_summary
            else ["No prior patient-level longitudinal workflow memory available."]
        )

        markdown = "\n".join(
            [
                f"# X-Diabetes {audience.title()} Report",
                "",
                f"- **Patient ID**: {patient_context.patient_id}",
                f"- **Task**: {task}",
                f"- **Question**: {clinical_question or 'General diabetes review'}",
                f"- **DTMH backend**: {dtmh_result.backend}",
                f"- **Generated at**: {datetime.now(UTC).isoformat()}",
                "",
                "## Patient Context",
                patient_context.summary,
                "",
                "## Longitudinal Memory",
                *longitudinal_lines,
                "",
                "## DTMH Summary",
                dtmh_result.summary,
                "",
                "## Organ State Snapshot",
                *organ_lines,
                "",
                "## Suggested Next Steps",
                *next_step_lines,
                "",
                "## Evidence Highlights",
                *evidence_lines,
                "",
                "## Knowledge Retrieval",
                *knowledge_lines,
                "",
                "## Safety Gate",
                f"- **Overall status**: {safety.overall_status}",
                *safety_lines,
                "",
                "## Disclaimer",
                safety.disclaimer,
            ]
        )

        saved_path = ""
        if save_report:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"{DEFAULT_REPORT_FILENAME_PREFIX}_{patient_context.patient_id}_{timestamp}.md"
            path = self._reports_dir / filename
            path.write_text(markdown, encoding="utf-8")
            saved_path = str(path)

        return ReportArtifact(audience=audience, markdown=markdown, saved_path=saved_path)
