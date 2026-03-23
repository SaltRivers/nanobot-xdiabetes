"""Patient longitudinal memory inspection tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.services import PatientMemoryStore

from .common import dump_json


class XDiabetesPatientMemoryTool(Tool):
    """Inspect persisted patient-level workflow memory."""

    def __init__(self, *, patient_memory_store: PatientMemoryStore, timeline_max_read: int = 10):
        self._patient_memory_store = patient_memory_store
        self._timeline_max_read = timeline_max_read

    @property
    def name(self) -> str:
        return "xdiabetes_patient_memory"

    @property
    def description(self) -> str:
        return (
            "Inspect patient-level longitudinal workflow memory, including the latest persisted snapshot, "
            "recent timeline events, and the human-readable summary."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier whose longitudinal memory should be loaded.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent events to return.",
                    "minimum": 1,
                    "maximum": 50,
                },
                "task": {
                    "type": "string",
                    "description": "Optional task hint used to prefer relevant timeline events.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
            },
            "required": ["patient_id"],
        }

    async def execute(self, patient_id: str, limit: int = 10, task: str = "general", **_: Any) -> str:
        recent_events = self._patient_memory_store.load_recent_timeline(
            patient_id,
            limit=min(max(1, limit), 50),
            task=task,
        )
        latest_snapshot = self._patient_memory_store.load_latest_snapshot(patient_id)
        summary_markdown = self._patient_memory_store.read_summary(patient_id)
        profile = self._patient_memory_store.load_profile(patient_id)
        return dump_json(
            {
                "patient_id": patient_id,
                "profile": profile.model_dump(mode="json") if profile else {},
                "latest_snapshot": latest_snapshot.model_dump(mode="json") if latest_snapshot else {},
                "summary_markdown": summary_markdown,
                "recent_events": [item.model_dump(mode="json") for item in recent_events],
            }
        )
