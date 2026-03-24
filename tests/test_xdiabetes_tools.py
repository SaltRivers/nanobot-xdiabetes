from pathlib import Path
from unittest.mock import MagicMock

import pytest

from xdiabetes.agent.loop import AgentLoop
from xdiabetes.bus.queue import MessageBus
from xdiabetes.agent.tools.registry import ToolRegistry
from xdiabetes.config.schema import XDiabetesConfig
from xdiabetes.x_diabetes import prepare_xdiabetes_workspace, register_x_diabetes_tools


def test_prepare_xdiabetes_workspace_creates_seed_assets(tmp_path: Path):
    created = prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "USER.md").exists()
    assert (tmp_path / "cases" / "demo_patient.json").exists()
    assert (tmp_path / "knowledge" / "manifest.json").exists()
    assert (tmp_path / "rules" / "default_rules.json").exists()
    assert (tmp_path / "patient_memory").exists()
    assert (tmp_path / "learning" / "observations").exists()
    assert (tmp_path / "learning" / "policies" / "default_learning_policy.json").exists()
    assert created


@pytest.mark.asyncio
async def test_xdiabetes_consultation_tool_runs_end_to_end(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    registry = ToolRegistry()
    config = XDiabetesConfig(enabled=True, mode="doctor")
    register_x_diabetes_tools(registry, workspace=tmp_path, config=config)

    result = await registry.execute(
        "xdiabetes_consultation",
        {
            "patient_id": "demo_patient",
            "clinical_question": "Review the complication risks and create a doctor report",
            "task": "complication",
            "audience": "doctor",
            "save_report": True,
        },
    )

    assert "X-Diabetes Consultation Result" in result
    assert "mock" in result
    reports = list((tmp_path / "reports").glob("xdiabetes_report_demo_patient_*.md"))
    assert reports
    patient_memory_dir = tmp_path / "patient_memory" / "demo_patient"
    assert (patient_memory_dir / "summary.md").exists()
    assert (patient_memory_dir / "latest_snapshot.json").exists()


def test_agent_loop_registers_xdiabetes_tools_even_when_legacy_enabled_flag_is_false(tmp_path: Path):
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"

    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        x_diabetes_config=XDiabetesConfig(enabled=False),
    )

    assert "xdiabetes_consultation" in loop.tools.tool_names
