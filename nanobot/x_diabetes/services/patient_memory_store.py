"""Persistent patient-level longitudinal memory for X-Diabetes.

This module intentionally keeps storage file-based and human-inspectable so the
MVP remains easy to debug and audit. Each patient gets an isolated directory
with JSON/JSONL artifacts that can later be migrated to a database-backed
implementation without changing the agent/tool contracts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from nanobot.x_diabetes.errors import PatientMemoryError
from nanobot.x_diabetes.schemas import (
    DTMHResult,
    EncounterRecord,
    KnowledgeHit,
    KnowledgeRetrievalMetadata,
    PatientCase,
    PatientContext,
    PatientLongitudinalSnapshot,
    PatientMemoryProfile,
    PatientTimelineEvent,
    ReportArtifact,
    ReportIndexRecord,
    RiskAssessmentRecord,
    SafetyAssessment,
)

_PATIENT_KEY_RE = re.compile(r"[^a-zA-Z0-9._-]+")


class PatientMemoryStore:
    """File-backed longitudinal storage keyed by patient identifier."""

    def __init__(
        self,
        root_dir: Path,
        *,
        summary_filename: str = "summary.md",
        write_encounter: bool = True,
        write_risk_assessment: bool = True,
        write_report_index: bool = True,
    ):
        self._root_dir = root_dir
        self._summary_filename = summary_filename
        self._write_encounter = write_encounter
        self._write_risk_assessment = write_risk_assessment
        self._write_report_index = write_report_index
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def sync_profile(self, patient: PatientCase) -> Path:
        """Create or refresh the patient profile from the latest case data."""
        profile = self.load_profile(patient.patient_id)
        now = PatientMemoryProfile(patient_id=patient.patient_id).updated_at
        if profile is None:
            profile = PatientMemoryProfile(
                patient_id=patient.patient_id,
                demographics=patient.demographics,
                updated_at=now,
            )
        else:
            profile.demographics = patient.demographics
            profile.updated_at = now
        path = self._profile_path(patient.patient_id)
        self._write_json(path, profile.model_dump(mode="json"))
        return path

    def load_profile(self, patient_id: str) -> PatientMemoryProfile | None:
        """Load the stored patient profile if present."""
        path = self._profile_path(patient_id)
        if not path.exists():
            return None
        return PatientMemoryProfile.model_validate(self._read_json(path))

    def load_latest_snapshot(self, patient_id: str) -> PatientLongitudinalSnapshot | None:
        """Load the most recent workflow-derived patient snapshot if present."""
        path = self._latest_snapshot_path(patient_id)
        if not path.exists():
            return None
        return PatientLongitudinalSnapshot.model_validate(self._read_json(path))

    def save_latest_snapshot(self, snapshot: PatientLongitudinalSnapshot) -> Path:
        """Persist the newest patient-level derived snapshot."""
        path = self._latest_snapshot_path(snapshot.patient_id)
        self._write_json(path, snapshot.model_dump(mode="json"))
        return path

    def read_summary(self, patient_id: str) -> str:
        """Read the human-facing longitudinal markdown summary."""
        path = self._summary_path(patient_id)
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - rare filesystem failure
            raise PatientMemoryError(f"Failed to read patient summary: {path}") from exc

    def write_summary(self, patient_id: str, summary_markdown: str) -> Path:
        """Persist the human-facing longitudinal markdown summary."""
        path = self._summary_path(patient_id)
        self._write_text(path, summary_markdown)
        return path

    def load_recent_timeline(
        self,
        patient_id: str,
        *,
        limit: int = 10,
        task: str | None = None,
    ) -> list[PatientTimelineEvent]:
        """Read the most recent timeline events, optionally preferring one task."""
        path = self._timeline_path(patient_id)
        if not path.exists():
            return []

        try:
            events = [
                PatientTimelineEvent.model_validate(json.loads(line))
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise PatientMemoryError(f"Failed to load patient timeline: {path}") from exc

        events.sort(key=lambda item: item.timestamp, reverse=True)
        if task and task != "general":
            task_events = [item for item in events if item.task == task]
            other_events = [item for item in events if item.task != task]
            events = task_events + other_events
        return events[: max(1, limit)]

    def append_timeline_event(self, event: PatientTimelineEvent) -> Path:
        """Append one timeline event to the patient's JSONL event log."""
        path = self._timeline_path(event.patient_id)
        self._append_jsonl(path, event.model_dump(mode="json"))
        return path

    def save_encounter(self, record: EncounterRecord) -> Path | None:
        """Persist one encounter record when encounter writes are enabled."""
        if not self._write_encounter:
            return None
        path = self._encounters_dir(record.patient_id) / f"{record.encounter_id}.json"
        self._write_json(path, record.model_dump(mode="json"))
        return path

    def save_risk_assessment(self, record: RiskAssessmentRecord) -> Path | None:
        """Persist one structured risk assessment when enabled."""
        if not self._write_risk_assessment:
            return None
        path = self._risk_dir(record.patient_id) / f"{record.assessment_id}.json"
        self._write_json(path, record.model_dump(mode="json"))
        return path

    def append_report_index(self, record: ReportIndexRecord) -> Path | None:
        """Append one report index record when report indexing is enabled."""
        if not self._write_report_index:
            return None
        path = self._reports_index_path(record.patient_id)
        self._append_jsonl(path, record.model_dump(mode="json"))
        return path

    def persist_consultation_artifacts(
        self,
        *,
        patient: PatientCase,
        patient_context: PatientContext,
        task: str,
        audience: str,
        clinical_question: str,
        report: ReportArtifact,
        dtmh_result: DTMHResult,
        safety: SafetyAssessment,
        evidence: list[KnowledgeHit],
        knowledge_metadata: KnowledgeRetrievalMetadata,
    ) -> dict[str, Path | None]:
        """Persist the main artifacts produced by one diabetes workflow run."""
        self.sync_profile(patient)

        timestamp = PatientLongitudinalSnapshot(patient_id=patient.patient_id).updated_at
        stem = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{task}"
        snapshot = PatientLongitudinalSnapshot(
            patient_id=patient.patient_id,
            updated_at=timestamp,
            latest_task=task,
            latest_clinical_question=clinical_question,
            latest_report_path=report.saved_path,
            latest_safety_status=safety.overall_status,
            latest_dtmh_backend=dtmh_result.backend,
            latest_patient_summary=patient_context.summary,
            latest_risk_profile=dtmh_result.risk_profile,
            latest_data_quality_flags=patient_context.data_quality_flags,
        )
        snapshot_path = self.save_latest_snapshot(snapshot)

        encounter = EncounterRecord(
            encounter_id=stem,
            patient_id=patient.patient_id,
            created_at=timestamp,
            task=task,
            audience=audience,
            clinical_question=clinical_question,
            patient_summary=patient_context.summary,
            report_path=report.saved_path,
            report_saved=bool(report.saved_path),
            safety_status=safety.overall_status,
            safety_flags=safety.flags,
            dtmh_backend=dtmh_result.backend,
            evidence_titles=[item.title for item in evidence],
            knowledge_metadata=knowledge_metadata,
            data_quality_flags=patient_context.data_quality_flags,
        )
        encounter_path = self.save_encounter(encounter)

        risk = RiskAssessmentRecord(
            assessment_id=stem,
            patient_id=patient.patient_id,
            created_at=timestamp,
            task=task,
            dtmh_backend=dtmh_result.backend,
            overall_status=safety.overall_status,
            risk_profile=dtmh_result.risk_profile,
            organ_states=dtmh_result.organ_states,
            safety_flags=safety.flags,
        )
        risk_path = self.save_risk_assessment(risk)

        report_index_path = None
        if report.saved_path:
            report_index = ReportIndexRecord(
                report_id=stem,
                patient_id=patient.patient_id,
                created_at=timestamp,
                task=task,
                audience=audience,
                report_path=report.saved_path,
            )
            report_index_path = self.append_report_index(report_index)

        self.append_timeline_event(
            PatientTimelineEvent(
                event_id=stem,
                patient_id=patient.patient_id,
                timestamp=timestamp,
                event_type="consultation",
                task=task,
                title=f"{task.title()} workflow completed",
                summary=(
                    f"safety={safety.overall_status}, evidence={len(evidence)}, "
                    f"rag_status={knowledge_metadata.status}, report_saved={'yes' if report.saved_path else 'no'}"
                ),
                payload={
                    "clinical_question": clinical_question,
                    "report_path": report.saved_path,
                    "dtmh_backend": dtmh_result.backend,
                    "knowledge_backend": knowledge_metadata.backend_used,
                },
            )
        )
        summary_path = self.refresh_summary(patient_id=patient.patient_id, patient=patient)
        return {
            "snapshot": snapshot_path,
            "encounter": encounter_path,
            "risk_assessment": risk_path,
            "report_index": report_index_path,
            "summary": summary_path,
        }

    def build_summary_markdown(
        self,
        *,
        patient_id: str,
        patient: PatientCase | None = None,
        max_events: int = 5,
    ) -> str:
        """Build a concise markdown summary from persisted longitudinal state."""
        profile = self.load_profile(patient_id)
        snapshot = self.load_latest_snapshot(patient_id)
        recent_events = self.load_recent_timeline(patient_id, limit=max_events)

        demographics = patient.demographics if patient else (profile.demographics if profile else {})
        age = demographics.get("age", "unknown")
        sex = demographics.get("sex", "unknown")
        bmi = demographics.get("bmi", "unknown")
        complications = patient.complications if patient else []

        lines = [
            "# Patient Longitudinal Summary",
            "",
            f"- **Patient ID**: {patient_id}",
            f"- **Demographics**: age={age}, sex={sex}, bmi={bmi}",
        ]
        if complications:
            lines.append(f"- **Known complications**: {complications}")
        if snapshot is not None:
            lines.extend(
                [
                    f"- **Last updated**: {snapshot.updated_at.isoformat()}",
                    f"- **Latest workflow**: {snapshot.latest_task}",
                    f"- **Latest safety status**: {snapshot.latest_safety_status or 'unknown'}",
                    f"- **Latest DTMH backend**: {snapshot.latest_dtmh_backend or 'unknown'}",
                ]
            )
            if snapshot.latest_report_path:
                lines.append(f"- **Latest report**: {snapshot.latest_report_path}")

        lines.extend(["", "## Latest Clinical Snapshot"])
        if snapshot and snapshot.latest_patient_summary:
            lines.append(snapshot.latest_patient_summary)
        else:
            lines.append("No prior consultation summary has been written yet.")

        lines.extend(["", "## Recent Events"])
        if recent_events:
            for event in recent_events:
                lines.append(
                    f"- [{event.timestamp.isoformat()}] ({event.task}/{event.event_type}) "
                    f"{event.title}: {event.summary}"
                )
        else:
            lines.append("- No prior longitudinal events recorded.")

        return "\n".join(lines)

    def refresh_summary(
        self,
        *,
        patient_id: str,
        patient: PatientCase | None = None,
        max_events: int = 5,
    ) -> Path:
        """Rebuild and persist the markdown summary for one patient."""
        summary = self.build_summary_markdown(patient_id=patient_id, patient=patient, max_events=max_events)
        return self.write_summary(patient_id, summary)

    def patient_dir(self, patient_id: str) -> Path:
        """Return the on-disk directory for one patient, creating it if needed."""
        safe_id = self._safe_patient_key(patient_id)
        path = self._root_dir / safe_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "encounters").mkdir(parents=True, exist_ok=True)
        (path / "risk_assessments").mkdir(parents=True, exist_ok=True)
        (path / "dtmh_states").mkdir(parents=True, exist_ok=True)
        return path

    def _profile_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "profile.json"

    def _summary_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / self._summary_filename

    def _latest_snapshot_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "latest_snapshot.json"

    def _timeline_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "timeline.jsonl"

    def _reports_index_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "reports_index.jsonl"

    def _encounters_dir(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "encounters"

    def _risk_dir(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "risk_assessments"

    def _safe_patient_key(self, patient_id: str) -> str:
        cleaned = _PATIENT_KEY_RE.sub("_", patient_id.strip())
        if not cleaned:
            raise PatientMemoryError("Patient identifier cannot be empty when creating patient memory.")
        return cleaned

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PatientMemoryError(f"Failed to read JSON file: {path}") from exc

    def _write_json(self, path: Path, payload: dict) -> None:
        self._write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError as exc:  # pragma: no cover - rare filesystem failure
            raise PatientMemoryError(f"Failed to append JSONL file: {path}") from exc

    def _write_text(self, path: Path, content: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:  # pragma: no cover - rare filesystem failure
            raise PatientMemoryError(f"Failed to write file: {path}") from exc
