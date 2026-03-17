import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from nanobot.cli.commands import app
from nanobot.config.schema import Config

runner = CliRunner()


def test_xdiabetes_onboard_creates_isolated_workspace(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("HOME", str(tmp_path))
    expected_workspace = tmp_path / ".nanobot" / "xdiabetes-workspace"

    def _save_config(config: Config, config_path=None):
        path = config_path or config_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config.model_dump(by_alias=True), ensure_ascii=False))

    with patch("nanobot.config.loader.get_config_path", return_value=config_file), \
         patch("nanobot.config.loader.save_config", side_effect=_save_config), \
         patch("nanobot.cli.commands._onboard_plugins"), \
         patch("nanobot.config.loader.load_config", return_value=Config()):
        result = runner.invoke(app, ["xdiabetes", "onboard"])

    assert result.exit_code == 0
    assert "X-Diabetes profile is ready" in result.stdout
    assert (expected_workspace / "cases" / "demo_patient.json").exists()
    assert (expected_workspace / "patient_memory").exists()
