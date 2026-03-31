"""Post-activation monitoring for learned X-Diabetes skills."""

from __future__ import annotations

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.clinical.learning.schemas import ActivatedSkillState, LearningObservation


class LearningMonitor:
    """Track whether activated learned skills keep behaving well over time."""

    def __init__(self, config: XDiabetesLearningConfig):
        self._config = config

    def update(
        self,
        state: dict[str, ActivatedSkillState],
        *,
        observation: LearningObservation,
        pattern_to_skills: dict[str, list[str]],
    ) -> dict[str, ActivatedSkillState]:
        """Update monitoring counters based on one new observation."""

        if not self._config.enable_post_activation_monitoring:
            return state

        matched_skills = pattern_to_skills.get(observation.pattern_key, [])
        for skill_name in matched_skills:
            record = state.get(skill_name)
            if record is None:
                continue
            record.usage_count += 1
            record.last_matched_pattern = observation.pattern_key
            if observation.correction_signal or observation.error_count > 0:
                record.contradiction_count += 1
                record.notes.append(
                    f"Observed contradiction after pattern {observation.pattern_key}: corrections={observation.correction_signal}, errors={observation.error_count}."
                )
            contradiction_rate = record.contradiction_count / max(record.usage_count, 1)
            if record.contradiction_count >= 2 and contradiction_rate >= 0.4:
                record.status = "needs_review"
                if self._config.auto_deactivate:
                    record.status = "deactivated"
                    record.notes.append("Auto-deactivation threshold reached; remove the live skill before next session.")
        return state
