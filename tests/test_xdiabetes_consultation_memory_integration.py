import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from xdiabetes.agent.tools.registry import ToolRegistry
from xdiabetes.config.schema import XDiabetesConfig
from xdiabetes.x_diabetes import prepare_xdiabetes_workspace, register_x_diabetes_tools


@pytest.mark.asyncio
async def test_consultation_persists_patient_memory_even_when_rag_api_fails(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    registry = ToolRegistry()
    config = XDiabetesConfig(enabled=True, mode="doctor")
    config.rag.backend = "api"
    config.rag.api_base_url = "http://127.0.0.1:8008"
    config.rag.ignore_failure = True
    register_x_diabetes_tools(registry, workspace=tmp_path, config=config)

    with patch(
        "xdiabetes.x_diabetes.services.rag_api_client.httpx.post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        result = await registry.execute(
            "xdiabetes_consultation",
            {
                "patient_id": "demo_patient",
                "clinical_question": "Review complication risks and persist the consultation",
                "task": "complication",
                "audience": "doctor",
                "save_report": True,
            },
        )

    assert "Knowledge Retrieval" in result
    assert "api_connection_error" in result

    patient_dir = tmp_path / "patient_memory" / "demo_patient"
    assert (patient_dir / "summary.md").exists()
    assert (patient_dir / "latest_snapshot.json").exists()
    encounter_files = sorted((patient_dir / "encounters").glob("*.json"))
    assert encounter_files

    encounter_payload = json.loads(encounter_files[-1].read_text(encoding="utf-8"))
    assert encounter_payload["knowledge_metadata"]["status"] == "api_connection_error"
    assert encounter_payload["report_saved"] is True
