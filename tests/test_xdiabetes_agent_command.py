from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from xdiabetes.cli.commands import app
from xdiabetes.config.schema import Config

runner = CliRunner()


def test_xdiabetes_agent_single_message_uses_profile_runtime(tmp_path: Path):
    config = Config()
    config.clinical.enabled = True
    config.clinical.workspace = str(tmp_path / "x-diabetes-workspace")

    with patch("xdiabetes.config.loader.load_config", return_value=config), \
         patch("xdiabetes.cli.commands._make_provider", return_value=object()), \
         patch("xdiabetes.config.paths.get_cron_dir", return_value=tmp_path / "cron"), \
         patch("xdiabetes.clinical.workspace.prepare_clinical_workspace"), \
         patch("xdiabetes.bus.queue.MessageBus"), \
         patch("xdiabetes.cron.service.CronService"), \
         patch("xdiabetes.agent.loop.AgentLoop") as mock_agent_loop_cls:
        agent_loop = MagicMock()
        agent_loop.channels_config = None
        agent_loop.process_direct = AsyncMock(return_value="xdiabetes-response")
        agent_loop.close_mcp = AsyncMock(return_value=None)
        mock_agent_loop_cls.return_value = agent_loop

        result = runner.invoke(
            app,
            ["xdiabetes", "agent", "-m", "Analyze demo_patient", "--mode", "doctor"],
        )

    assert result.exit_code == 0
    assert "xdiabetes-response" in result.stdout
    assert mock_agent_loop_cls.call_args.kwargs["x_diabetes_config"].enabled is True
    assert mock_agent_loop_cls.call_args.kwargs["workspace"] == Path(config.clinical.workspace)
