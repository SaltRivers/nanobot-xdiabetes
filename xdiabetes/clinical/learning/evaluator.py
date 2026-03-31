"""Evaluation pipeline for learned instincts and skill drafts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.clinical.learning.privacy import PrivacyFilter
from xdiabetes.clinical.learning.schemas import (
    LearningEvaluationResult,
    LearningInstinct,
    LearningPolicy,
    LearningSkillDraft,
)


class LearningEvaluator:
    """Run checklist- and threshold-based evaluations for learning artifacts."""

    def __init__(
        self,
        *,
        config: XDiabetesLearningConfig,
        policy: LearningPolicy,
        privacy_filter: PrivacyFilter,
        existing_skill_paths: list[Path],
    ):
        self._config = config
        self._policy = policy
        self._privacy_filter = privacy_filter
        self._existing_skills = [path.read_text(encoding="utf-8") for path in existing_skill_paths if path.exists()]

    def evaluate_instinct(self, instinct: LearningInstinct) -> LearningEvaluationResult:
        """Evaluate whether an instinct is strong and reusable enough to keep."""

        checklist = {
            "enough_evidence": instinct.evidence_count >= self._policy.min_observations_to_learn,
            "privacy_clean": instinct.evidence_count > 0,
            "reusable_pattern": instinct.task != "general" or instinct.domain in {"workflow", "communication", "reporting", "safety"},
            "low_contradiction": instinct.correction_rate <= 0.5,
            "low_error_rate": instinct.error_rate <= 0.5,
        }
        scores = {
            "evidence": min(1.0, instinct.evidence_count / max(self._policy.min_observations_to_learn, 1)),
            "confidence": instinct.confidence,
            "stability": round(max(0.0, 1.0 - instinct.correction_rate - instinct.error_rate), 3),
        }
        blocking_issues: list[str] = []
        warnings: list[str] = []
        verdict = "review"

        if not checklist["enough_evidence"]:
            warnings.append("need more repeated observations before promoting this instinct")
            verdict = "drop"
        elif not checklist["low_contradiction"]:
            warnings.append("user corrections are too frequent for this instinct")
            verdict = "revise"
        elif instinct.confidence >= self._config.min_confidence_to_draft:
            verdict = "approve"
        else:
            warnings.append("confidence is still below the draft threshold")
            verdict = "review"

        rationale = (
            f"Instinct '{instinct.instinct_id}' has {instinct.evidence_count} observations, "
            f"confidence {instinct.confidence:.0%}, correction rate {instinct.correction_rate:.0%}, "
            f"and error rate {instinct.error_rate:.0%}."
        )
        return LearningEvaluationResult(
            evaluation_id=self._evaluation_id("instinct", instinct.instinct_id),
            entity_type="instinct",
            entity_id=instinct.instinct_id,
            created_at=datetime.now(UTC),
            checklist=checklist,
            scores=scores,
            verdict=verdict,
            rationale=rationale,
            blocking_issues=blocking_issues,
            warnings=warnings,
            recommended_actions=["keep observing" if verdict in {"drop", "review"} else "eligible for draft generation"],
        )

    def evaluate_draft(self, draft: LearningSkillDraft) -> LearningEvaluationResult:
        """Evaluate a draft skill before it can be approved or activated."""

        issues = self._privacy_filter.find_skill_issues(draft.skill_markdown)
        similarity = self._max_similarity(draft.skill_markdown)
        passed_cases = self._run_synthetic_eval(draft)
        required_sections_ok = all(section in draft.skill_markdown for section in self._policy.required_skill_sections)
        safety_keywords_ok = all(keyword in draft.skill_markdown.lower() for keyword in self._policy.safety_keywords)
        checklist = {
            "no_privacy_leak": not issues,
            "required_sections": required_sections_ok,
            "safety_language": safety_keywords_ok,
            "non_redundant": similarity < self._config.max_similarity_before_conflict,
            "synthetic_eval": len(passed_cases) == len(self._applicable_cases(draft)),
        }
        scores = {
            "evidence": round(min(1.0, draft.confidence), 3),
            "reusability": round(min(1.0, 0.45 + draft.confidence * 0.55), 3),
            "privacy": 0.0 if issues else 1.0,
            "safety": 1.0 if safety_keywords_ok else 0.4,
            "conflict": round(similarity, 3),
        }

        blocking_issues = list(issues)
        warnings: list[str] = []
        verdict = "review"
        if issues:
            verdict = "drop"
        elif not required_sections_ok:
            warnings.append("draft is missing one or more required skill sections")
            verdict = "revise"
        elif similarity >= self._config.max_similarity_before_conflict:
            warnings.append("draft overlaps too heavily with an existing skill")
            verdict = "revise"
        elif not checklist["synthetic_eval"]:
            warnings.append("draft did not satisfy all synthetic activation checks")
            verdict = "revise"
        elif self._config.require_human_approval:
            verdict = "review"
        elif self._config.auto_activate:
            verdict = "activate"
        else:
            verdict = "approve"

        rationale = (
            f"Draft '{draft.draft_id}' scored evidence={scores['evidence']:.2f}, "
            f"reusability={scores['reusability']:.2f}, privacy={scores['privacy']:.2f}, "
            f"safety={scores['safety']:.2f}, conflict={scores['conflict']:.2f}."
        )
        recommended_actions = [
            "request human review before activation" if verdict == "review" else "draft is ready to move forward"
        ]
        if verdict == "revise":
            recommended_actions = ["revise the draft and re-run evaluation"]
        if verdict == "drop":
            recommended_actions = ["drop this draft; it is not safe to save"]

        return LearningEvaluationResult(
            evaluation_id=self._evaluation_id("draft", draft.draft_id),
            entity_type="draft",
            entity_id=draft.draft_id,
            created_at=datetime.now(UTC),
            checklist=checklist,
            scores=scores,
            verdict=verdict,
            rationale=rationale,
            blocking_issues=blocking_issues,
            warnings=warnings,
            recommended_actions=recommended_actions,
            synthetic_cases_passed=passed_cases,
        )

    def evaluate_activation(self, draft: LearningSkillDraft) -> LearningEvaluationResult:
        """Run a final activation gate before copying the skill into the workspace."""

        draft_evaluation = self.evaluate_draft(draft)
        checklist = dict(draft_evaluation.checklist)
        checklist["activation_allowed"] = draft_evaluation.verdict in {"review", "approve", "activate"} and not draft_evaluation.blocking_issues
        warnings = list(draft_evaluation.warnings)
        blocking_issues = list(draft_evaluation.blocking_issues)
        verdict = "activate" if checklist["activation_allowed"] else "drop"
        rationale = (
            f"Activation gate {'passed' if checklist['activation_allowed'] else 'failed'} for draft '{draft.draft_id}'."
        )
        return LearningEvaluationResult(
            evaluation_id=self._evaluation_id("activation", draft.draft_id),
            entity_type="activation",
            entity_id=draft.draft_id,
            created_at=datetime.now(UTC),
            checklist=checklist,
            scores=dict(draft_evaluation.scores),
            verdict=verdict,
            rationale=rationale,
            blocking_issues=blocking_issues,
            warnings=warnings,
            recommended_actions=["activate draft" if verdict == "activate" else "fix blockers before activation"],
            synthetic_cases_passed=list(draft_evaluation.synthetic_cases_passed),
        )

    def _max_similarity(self, content: str) -> float:
        if not self._existing_skills:
            return 0.0
        return max(SequenceMatcher(a=existing, b=content).ratio() for existing in self._existing_skills)

    def _applicable_cases(self, draft: LearningSkillDraft) -> list[dict]:
        applicable: list[dict] = []
        for case in self._policy.synthetic_eval_cases:
            modes = case.get("modes", [draft.mode])
            domains = case.get("domains", [draft.domain])
            if draft.mode in modes and draft.domain in domains:
                applicable.append(case)
        return applicable

    def _run_synthetic_eval(self, draft: LearningSkillDraft) -> list[str]:
        passed: list[str] = []
        lowered = draft.skill_markdown.lower()
        for case in self._applicable_cases(draft):
            markers = [marker.lower() for marker in case.get("required_markers", [])]
            if all(marker in lowered for marker in markers):
                passed.append(str(case.get("id", "synthetic-case")))
        return passed

    @staticmethod
    def _evaluation_id(entity_type: str, entity_id: str) -> str:
        seed = f"{entity_type}:{entity_id}:{datetime.now(UTC).isoformat()}"
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def discover_existing_skill_paths(workspace: Path) -> list[Path]:
    """Return built-in and workspace skill files for conflict comparison."""

    paths = list((workspace / "skills").glob("*/SKILL.md"))
    builtin = Path(__file__).resolve().parents[2] / "skills" / "x-diabetes" / "SKILL.md"
    if builtin.exists():
        paths.append(builtin)
    return sorted({path.resolve() for path in paths})


def load_synthetic_cases(path: Path) -> list[dict]:
    """Load synthetic evaluation cases from the workspace template."""

    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
