"""Storage helpers for X-Diabetes continuous learning."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TypeVar

from nanobot.x_diabetes.learning.schemas import (
    ActivatedSkillState,
    LearningEvaluationResult,
    LearningInstinct,
    LearningObservation,
    LearningSkillDraft,
)

ModelT = TypeVar("ModelT", LearningObservation, LearningInstinct, LearningSkillDraft, LearningEvaluationResult)


class LearningStore:
    """Read and write continuous-learning artifacts using JSON/JSONL files."""

    def __init__(self, learning_root: Path):
        self.root = learning_root
        self.observations_file = self.root / "observations" / "observations.jsonl"
        self.instincts_dir = self.root / "instincts"
        self.drafts_dir = self.root / "drafts"
        self.evaluations_dir = self.root / "evaluations"
        self.approved_dir = self.root / "approved"
        self.rejected_dir = self.root / "rejected"
        self.rollback_dir = self.root / "rollback"
        self.state_dir = self.root / "state"
        self.policies_dir = self.root / "policies"
        self.evals_dir = self.root / "evals"
        for path in (
            self.observations_file.parent,
            self.instincts_dir,
            self.drafts_dir,
            self.evaluations_dir / "instincts",
            self.evaluations_dir / "drafts",
            self.evaluations_dir / "activations",
            self.approved_dir,
            self.rejected_dir,
            self.rollback_dir,
            self.state_dir,
            self.policies_dir,
            self.evals_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def append_observation(self, observation: LearningObservation) -> Path:
        self._append_jsonl(self.observations_file, observation.model_dump(mode="json"))
        return self.observations_file

    def load_observations(self) -> list[LearningObservation]:
        return self._read_jsonl(self.observations_file, LearningObservation)

    def save_instinct(self, instinct: LearningInstinct) -> Path:
        path = self.instincts_dir / f"{instinct.instinct_id}.json"
        self._write_json(path, instinct.model_dump(mode="json"))
        return path

    def load_instincts(self) -> list[LearningInstinct]:
        return self._read_json_dir(self.instincts_dir, LearningInstinct)

    def save_draft(self, draft: LearningSkillDraft) -> Path:
        draft_dir = self.drafts_dir / draft.draft_id
        draft_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(draft_dir / "draft.json", draft.model_dump(mode="json"))
        (draft_dir / "SKILL.md").write_text(draft.skill_markdown, encoding="utf-8")
        return draft_dir

    def load_drafts(self) -> list[LearningSkillDraft]:
        drafts: list[LearningSkillDraft] = []
        if not self.drafts_dir.exists():
            return drafts
        for draft_dir in sorted(self.drafts_dir.iterdir()):
            if not draft_dir.is_dir():
                continue
            path = draft_dir / "draft.json"
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            drafts.append(LearningSkillDraft.model_validate(payload))
        return drafts

    def load_draft(self, draft_id: str) -> LearningSkillDraft | None:
        path = self.drafts_dir / draft_id / "draft.json"
        if not path.exists():
            return None
        return LearningSkillDraft.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_evaluation(self, evaluation: LearningEvaluationResult) -> Path:
        target_dir = self.evaluations_dir / f"{evaluation.entity_type}s"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{evaluation.entity_id}.json"
        self._write_json(path, evaluation.model_dump(mode="json"))
        return path

    def load_evaluation(self, entity_type: str, entity_id: str) -> LearningEvaluationResult | None:
        path = self.evaluations_dir / f"{entity_type}s" / f"{entity_id}.json"
        if not path.exists():
            return None
        return LearningEvaluationResult.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def load_activated_skill_state(self) -> dict[str, ActivatedSkillState]:
        path = self.state_dir / "activated_skills.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {name: ActivatedSkillState.model_validate(item) for name, item in payload.items()}

    def save_activated_skill_state(self, state: dict[str, ActivatedSkillState]) -> Path:
        path = self.state_dir / "activated_skills.json"
        payload = {name: item.model_dump(mode="json") for name, item in state.items()}
        self._write_json(path, payload)
        return path

    def mark_approved(self, draft_id: str, payload: dict) -> Path:
        path = self.approved_dir / f"{draft_id}.json"
        self._write_json(path, payload)
        return path

    def mark_rejected(self, draft_id: str, payload: dict) -> Path:
        path = self.rejected_dir / f"{draft_id}.json"
        self._write_json(path, payload)
        return path

    def list_json_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(path for path in directory.glob("*.json") if path.is_file())

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path, model: type[ModelT]) -> list[ModelT]:
        if not path.exists():
            return []
        items: list[ModelT] = []
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                items.append(model.model_validate(json.loads(line)))
        return items

    def _read_json_dir(self, directory: Path, model: type[ModelT]) -> list[ModelT]:
        if not directory.exists():
            return []
        items: list[ModelT] = []
        for path in sorted(directory.glob("*.json")):
            items.append(model.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items
