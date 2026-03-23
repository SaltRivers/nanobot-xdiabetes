import asyncio
import json
from pathlib import Path

from xdiabetes.agent.tools.registry import ToolRegistry
from xdiabetes.config.schema import XDiabetesConfig
from xdiabetes.x_diabetes import prepare_xdiabetes_workspace, register_x_diabetes_tools


def test_xdiabetes_patient_context_exposes_longitudinal_memory(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    registry = ToolRegistry()
    config = XDiabetesConfig(enabled=True, mode="doctor")
    register_x_diabetes_tools(registry, workspace=tmp_path, config=config)

    asyncio.run(
        registry.execute(
            "xdiabetes_consultation",
            {
                "patient_id": "demo_patient",
                "clinical_question": "Review renal risk and generate a report",
                "task": "complication",
                "audience": "doctor",
                "save_report": True,
            },
        )
    )

    raw_context = asyncio.run(
        registry.execute(
            "xdiabetes_patient_context",
            {
                "patient_id": "demo_patient",
                "task": "complication",
                "clinical_question": "Review renal risk and generate a report",
            },
        )
    )
    payload = json.loads(raw_context)

    assert payload["patient_id"] == "demo_patient"
    assert payload["longitudinal_summary"]
    assert payload["recent_events"]
    assert "_longitudinal_memory" in payload["structured_data"]

    raw_memory = asyncio.run(
        registry.execute(
            "xdiabetes_patient_memory",
            {"patient_id": "demo_patient", "limit": 5, "task": "complication"},
        )
    )
    memory_payload = json.loads(raw_memory)
    assert "Patient Longitudinal Summary" in memory_payload["summary_markdown"]
    assert memory_payload["recent_events"]
