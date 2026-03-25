"""Compatibility coverage for renamed built-in skill paths."""

from pathlib import Path

from xdiabetes.agent.skills import SkillsLoader


def _make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    return workspace


def test_builtin_skills_use_canonical_clinical_playbook_name(tmp_path) -> None:
    """The built-in skill list should expose the canonical first-party path name."""
    loader = SkillsLoader(_make_workspace(tmp_path))

    names = {skill["name"] for skill in loader.list_skills(filter_unavailable=False)}

    assert "clinical-playbook" in names
    assert "x-diabetes" not in names


def test_legacy_x_diabetes_skill_alias_still_loads_builtin_playbook(tmp_path) -> None:
    """Legacy callers should still resolve the renamed built-in clinical playbook."""
    loader = SkillsLoader(_make_workspace(tmp_path))

    assert loader.load_skill("clinical-playbook") == loader.load_skill("x-diabetes")
