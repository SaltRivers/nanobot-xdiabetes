"""Context-building helpers that inject patient-level longitudinal memory."""

from __future__ import annotations

from nanobot.x_diabetes.schemas import PatientCase, PatientContext
from nanobot.x_diabetes.services.patient_memory_store import PatientMemoryStore


class PatientMemoryBuilder:
    """Merge the raw patient case with persisted longitudinal memory."""

    def __init__(self, memory_store: PatientMemoryStore, *, timeline_max_read: int = 10):
        self._memory_store = memory_store
        self._timeline_max_read = timeline_max_read

    def initialize_patient(self, patient: PatientCase) -> None:
        """Ensure a patient has a durable memory directory and profile."""
        self._memory_store.sync_profile(patient)
        if not self._memory_store.read_summary(patient.patient_id):
            self._memory_store.refresh_summary(patient_id=patient.patient_id, patient=patient)

    def build_context(
        self,
        patient: PatientCase,
        base_context: PatientContext,
        *,
        task: str = "general",
        clinical_question: str = "",
    ) -> PatientContext:
        """Attach patient-level history without exploding the prompt size."""
        self.initialize_patient(patient)

        summary_markdown = self._memory_store.read_summary(patient.patient_id)
        latest_snapshot = self._memory_store.load_latest_snapshot(patient.patient_id)
        recent_events = self._memory_store.load_recent_timeline(
            patient.patient_id,
            limit=self._timeline_max_read,
            task=task,
        )

        longitudinal_parts: list[str] = []
        if latest_snapshot and latest_snapshot.latest_patient_summary:
            longitudinal_parts.append(f"Latest persisted review: {latest_snapshot.latest_patient_summary}")
        if recent_events:
            rendered_events = "; ".join(
                f"{item.task}/{item.event_type} on {item.timestamp.date()}: {item.summary}" for item in recent_events[:3]
            )
            longitudinal_parts.append(f"Recent longitudinal events: {rendered_events}")
        if not longitudinal_parts:
            longitudinal_parts.append(
                "No prior patient-specific longitudinal workflow memory is available yet in the workspace."
            )
        if clinical_question.strip():
            longitudinal_parts.append(f"Current question focus: {clinical_question.strip()}")

        longitudinal_summary = " ".join(longitudinal_parts).strip()
        merged_structured_data = dict(base_context.structured_data)
        merged_structured_data["_longitudinal_memory"] = {
            "summary_markdown": summary_markdown,
            "latest_snapshot": latest_snapshot.model_dump(mode="json") if latest_snapshot else {},
            "recent_events": [item.model_dump(mode="json") for item in recent_events],
        }

        return PatientContext(
            patient_id=base_context.patient_id,
            summary=(
                base_context.summary
                if not longitudinal_summary
                else f"{base_context.summary} Longitudinal context: {longitudinal_summary}"
            ),
            available_modalities=base_context.available_modalities,
            missing_modalities=base_context.missing_modalities,
            data_quality_flags=base_context.data_quality_flags,
            longitudinal_summary=longitudinal_summary,
            recent_events=recent_events,
            structured_data=merged_structured_data,
        )
