"""Top-level X-Diabetes continuous-learning service."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.clinical.errors import LearningError
from xdiabetes.clinical.learning.activation import LearningActivationManager
from xdiabetes.clinical.learning.analyzer import analyze_observations
from xdiabetes.clinical.learning.collector import collect_turn_observation
from xdiabetes.clinical.learning.evaluator import (
    LearningEvaluator,
    discover_existing_skill_paths,
    load_synthetic_cases,
)
from xdiabetes.clinical.learning.evolver import evolve_instincts_to_drafts
from xdiabetes.clinical.learning.monitor import LearningMonitor
from xdiabetes.clinical.learning.policy import load_learning_policy
from xdiabetes.clinical.learning.privacy import PrivacyFilter, discover_case_ids
from xdiabetes.clinical.learning.schemas import (
    ActivatedSkillState,
    LearningEvaluationResult,
    LearningSkillDraft,
    LearningStatusSnapshot,
)
from xdiabetes.clinical.learning.store import LearningStore


class XDiabetesLearningService:
    """Continuous-learning pipeline with privacy, evaluation, and activation gates."""

    def __init__(self, *, workspace: Path, config: XDiabetesLearningConfig, mode: str = "doctor"):
        self.workspace = workspace
        self.config = config
        self.mode = "patient" if mode == "patient" else "doctor"
        self.learning_root = self._resolve_learning_root(workspace, config.learning_dir)
        self.store = LearningStore(self.learning_root)
        self.policy = load_learning_policy(self.store.policies_dir / "default_learning_policy.json", config)
        synthetic_cases = load_synthetic_cases(self.store.evals_dir / "synthetic_skill_eval_cases.json")
        if synthetic_cases:
            self.policy.synthetic_eval_cases = synthetic_cases
        self.privacy_filter = PrivacyFilter(self.policy, discover_case_ids(self.workspace / "cases"))
        self.activation_manager = LearningActivationManager(workspace=self.workspace, rollback_dir=self.store.rollback_dir)
        self.monitor = LearningMonitor(config)

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    def record_turn(
        self,
        *,
        session_key: str,
        current_message: str,
        tools_used: list[str],
        all_messages: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Capture one turn, update instincts/drafts, and refresh monitoring state."""

        if not self.enabled:
            return None

        observation = collect_turn_observation(
            session_key=session_key,
            mode=self.mode,
            current_message=current_message,
            tools_used=tools_used,
            all_messages=all_messages,
            privacy_filter=self.privacy_filter,
        )
        if observation is None:
            return None

        self.store.append_observation(observation)
        observations = self.store.load_observations()
        instincts = analyze_observations(observations, self.policy, self.config)
        evaluator = self._build_evaluator()
        for instinct in instincts:
            self.store.save_instinct(instinct)
            self.store.save_evaluation(evaluator.evaluate_instinct(instinct))

        existing_drafts = self.store.load_drafts()
        new_drafts = evolve_instincts_to_drafts(instincts, existing_drafts)
        for draft in new_drafts:
            self.store.save_draft(draft)
            draft_eval = evaluator.evaluate_draft(draft)
            self.store.save_evaluation(draft_eval)
            if draft_eval.verdict == "activate" and self.config.auto_activate and not self.config.require_human_approval:
                try:
                    self.activate_draft(draft.draft_id, auto=True)
                except Exception as exc:  # pragma: no cover - defensive logging path
                    logger.warning("Auto-activation failed for draft {}: {}", draft.draft_id, exc)

        state = self.store.load_activated_skill_state()
        state = self.monitor.update(
            state,
            observation=observation,
            pattern_to_skills=self._pattern_to_skills(state),
        )
        self._apply_auto_deactivation(state)
        self.store.save_activated_skill_state(state)
        return {
            "observation_id": observation.observation_id,
            "instincts": len(instincts),
            "new_drafts": len(new_drafts),
        }

    def status_snapshot(self) -> LearningStatusSnapshot:
        """Return an aggregate snapshot for CLI output."""

        observations = self.store.load_observations()
        drafts = self.store.load_drafts()
        state = self.store.load_activated_skill_state()
        return LearningStatusSnapshot(
            enabled=self.config.enabled,
            strict_privacy=self.config.strict_privacy,
            require_human_approval=self.config.require_human_approval,
            auto_activate=self.config.auto_activate,
            observations=len(observations),
            instincts=len(self.store.load_instincts()),
            drafts=len(drafts),
            approved_drafts=sum(1 for draft in drafts if draft.status == "approved"),
            rejected_drafts=sum(1 for draft in drafts if draft.status == "rejected"),
            active_skills=sorted(name for name, record in state.items() if record.status == "active"),
            skills_needing_review=sorted(name for name, record in state.items() if record.status == "needs_review"),
            last_observation_at=observations[-1].created_at if observations else None,
        )

    def reviewable_drafts(self) -> list[tuple[LearningSkillDraft, LearningEvaluationResult | None]]:
        """List drafts together with their latest stored evaluation."""

        drafts = self.store.load_drafts()
        return [
            (draft, self.store.load_evaluation("draft", draft.draft_id))
            for draft in drafts
        ]

    def evaluate_draft(self, draft_id: str) -> LearningEvaluationResult:
        """Re-run evaluation for one draft and persist the result."""

        draft = self._require_draft(draft_id)
        result = self._build_evaluator().evaluate_draft(draft)
        self.store.save_evaluation(result)
        return result

    def approve_draft(self, draft_id: str) -> LearningSkillDraft:
        """Mark a draft as approved after it passes evaluation."""

        draft = self._require_draft(draft_id)
        result = self.evaluate_draft(draft_id)
        if result.blocking_issues or result.verdict == "drop":
            raise LearningError(f"Draft {draft_id} cannot be approved: {', '.join(result.blocking_issues or ['evaluation failed'])}")
        draft.status = "approved"
        self.store.save_draft(draft)
        self.store.mark_approved(draft_id, {
            "draft_id": draft_id,
            "approved_at": result.created_at.isoformat(),
            "evaluation": result.model_dump(mode="json"),
        })
        return draft

    def reject_draft(self, draft_id: str, reason: str = "") -> LearningSkillDraft:
        """Reject a draft and persist the reason for auditability."""

        draft = self._require_draft(draft_id)
        draft.status = "rejected"
        self.store.save_draft(draft)
        self.store.mark_rejected(draft_id, {
            "draft_id": draft_id,
            "rejected_at": datetime.now(UTC).isoformat(),
            "reason": reason or "rejected by reviewer",
        })
        return draft

    def activate_draft(self, draft_id: str, *, auto: bool = False) -> Path:
        """Activate a draft skill inside the workspace skills directory."""

        draft = self._require_draft(draft_id)
        if self.config.require_human_approval and draft.status != "approved" and not auto:
            raise LearningError(f"Draft {draft_id} must be approved before activation.")
        evaluator = self._build_evaluator()
        activation_eval = evaluator.evaluate_activation(draft)
        self.store.save_evaluation(activation_eval)
        if activation_eval.verdict != "activate":
            raise LearningError(f"Draft {draft_id} failed activation checks.")
        path = self.activation_manager.activate(draft)
        draft.status = "activated"
        self.store.save_draft(draft)

        instincts = {instinct.instinct_id: instinct for instinct in self.store.load_instincts()}
        state = self.store.load_activated_skill_state()
        state[draft.skill_name] = ActivatedSkillState(
            skill_name=draft.skill_name,
            draft_id=draft.draft_id,
            source_instinct_ids=list(draft.source_instinct_ids),
            pattern_keys=[
                instincts[source_id].pattern_key
                for source_id in draft.source_instinct_ids
                if source_id in instincts
            ],
            notes=["Activated after passing the X-Diabetes learning quality gate."],
        )
        self.store.save_activated_skill_state(state)
        return path

    def deactivate_skill(self, skill_name: str) -> Path:
        """Deactivate one learned skill from the live workspace."""

        path = self.activation_manager.deactivate(skill_name)
        state = self.store.load_activated_skill_state()
        if skill_name in state:
            state[skill_name].status = "deactivated"
            state[skill_name].notes.append("Deactivated manually.")
            self.store.save_activated_skill_state(state)
        return path

    def rollback_skill(self, skill_name: str) -> Path:
        """Rollback one learned skill to its most recent backup."""

        path = self.activation_manager.rollback(skill_name)
        state = self.store.load_activated_skill_state()
        if skill_name in state:
            state[skill_name].status = "active"
            state[skill_name].notes.append("Rolled back to the latest backup.")
            self.store.save_activated_skill_state(state)
        return path

    def _apply_auto_deactivation(self, state: dict[str, ActivatedSkillState]) -> None:
        if not self.config.auto_deactivate:
            return
        for skill_name, record in state.items():
            if record.status != "deactivated":
                continue
            live_path = self.workspace / "skills" / skill_name
            if live_path.exists():
                self.activation_manager.deactivate(skill_name)
                record.notes.append("Live skill removed automatically after repeated contradictions.")

    def _pattern_to_skills(self, state: dict[str, ActivatedSkillState]) -> dict[str, list[str]]:
        mapping: dict[str, list[str]] = {}
        for skill_name, record in state.items():
            for pattern_key in record.pattern_keys:
                mapping.setdefault(pattern_key, []).append(skill_name)
        return mapping

    def _require_draft(self, draft_id: str) -> LearningSkillDraft:
        draft = self.store.load_draft(draft_id)
        if draft is None:
            raise LearningError(f"Draft not found: {draft_id}")
        return draft

    def _build_evaluator(self) -> LearningEvaluator:
        return LearningEvaluator(
            config=self.config,
            policy=self.policy,
            privacy_filter=self.privacy_filter,
            existing_skill_paths=discover_existing_skill_paths(self.workspace),
        )

    @staticmethod
    def _resolve_learning_root(workspace: Path, configured: str) -> Path:
        candidate = Path(configured).expanduser()
        return candidate if candidate.is_absolute() else workspace / candidate
