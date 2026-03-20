from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from nanobot.cli.commands import app
from nanobot.config.schema import Config

runner = CliRunner()


def test_xdiabetes_agent_learning_flag_overrides_runtime(tmp_path: Path):
    config = Config()
    config.x_diabetes.enabled = True
    config.x_diabetes.workspace = str(tmp_path / "xdiabetes-workspace")
    config.x_diabetes.learning.enabled = False

    with patch("nanobot.config.loader.load_config", return_value=config), \
         patch("nanobot.cli.commands._make_provider", return_value=object()), \
         patch("nanobot.config.paths.get_cron_dir", return_value=tmp_path / "cron"), \
         patch("nanobot.x_diabetes.workspace.prepare_xdiabetes_workspace"), \
         patch("nanobot.bus.queue.MessageBus"), \
         patch("nanobot.cron.service.CronService"), \
         patch("nanobot.agent.loop.AgentLoop") as mock_agent_loop_cls:
        agent_loop = MagicMock()
        agent_loop.channels_config = None
        agent_loop.process_direct = AsyncMock(return_value="learning-flag-response")
        agent_loop.close_mcp = AsyncMock(return_value=None)
        mock_agent_loop_cls.return_value = agent_loop

        result = runner.invoke(
            app,
            ["xdiabetes", "agent", "-m", "Analyze demo_patient", "--mode", "doctor", "--learning"],
        )

    assert result.exit_code == 0
    assert mock_agent_loop_cls.call_args.kwargs["x_diabetes_config"].learning.enabled is True


def test_xdiabetes_learning_status_command_renders(tmp_path: Path):
    workspace = tmp_path / "xdiabetes-workspace"
    config = Config()
    config.x_diabetes.enabled = True
    config.x_diabetes.workspace = str(workspace)
    config.x_diabetes.learning.enabled = True

    with patch("nanobot.config.loader.load_config", return_value=config):
        result = runner.invoke(app, ["xdiabetes", "learning", "status"])

    assert result.exit_code == 0
    assert "X-Diabetes Continuous Learning" in result.stdout
