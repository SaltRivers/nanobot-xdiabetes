"""Activation and rollback helpers for learned X-Diabetes skills."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from nanobot.x_diabetes.errors import LearningError
from nanobot.x_diabetes.learning.schemas import LearningSkillDraft


class LearningActivationManager:
    """Approve, activate, deactivate, and roll back learned skills."""

    def __init__(self, *, workspace: Path, rollback_dir: Path):
        self._workspace = workspace
        self._skills_dir = workspace / "skills"
        self._rollback_dir = rollback_dir
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._rollback_dir.mkdir(parents=True, exist_ok=True)

    def activate(self, draft: LearningSkillDraft) -> Path:
        """Copy a draft skill into the live workspace, backing up any prior version."""

        destination_dir = self._skills_dir / draft.skill_name
        destination_dir.parent.mkdir(parents=True, exist_ok=True)
        if destination_dir.exists():
            self._backup_existing_skill(draft.skill_name, destination_dir)
            shutil.rmtree(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        (destination_dir / "SKILL.md").write_text(draft.skill_markdown, encoding="utf-8")
        return destination_dir

    def deactivate(self, skill_name: str) -> Path:
        """Move an active learned skill out of the live workspace."""

        source_dir = self._skills_dir / skill_name
        if not source_dir.exists():
            raise LearningError(f"Learned skill not found in workspace: {skill_name}")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        destination = self._rollback_dir / skill_name / f"deactivated_{timestamp}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_dir), str(destination))
        return destination

    def rollback(self, skill_name: str) -> Path:
        """Restore the latest backup for one learned skill."""

        history_dir = self._rollback_dir / skill_name
        if not history_dir.exists():
            raise LearningError(f"No rollback history found for learned skill: {skill_name}")
        backups = sorted(path for path in history_dir.iterdir() if path.is_dir())
        if not backups:
            raise LearningError(f"Rollback history is empty for learned skill: {skill_name}")
        latest = backups[-1]
        live_dir = self._skills_dir / skill_name
        if live_dir.exists():
            self._backup_existing_skill(skill_name, live_dir)
            shutil.rmtree(live_dir)
        shutil.copytree(latest, live_dir)
        return live_dir

    def _backup_existing_skill(self, skill_name: str, source_dir: Path) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_dir = self._rollback_dir / skill_name / timestamp
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, backup_dir)
        return backup_dir
