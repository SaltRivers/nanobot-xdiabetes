from pathlib import Path

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.x_diabetes.learning import XDiabetesLearningService
from xdiabetes.x_diabetes.learning.policy import build_default_policy
from xdiabetes.x_diabetes.learning.privacy import PrivacyFilter, discover_case_ids
from xdiabetes.x_diabetes.workspace import prepare_xdiabetes_workspace


def test_privacy_filter_redacts_secrets_and_case_ids(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)
    config = XDiabetesLearningConfig(enabled=True)
    policy = build_default_policy(config)
    privacy = PrivacyFilter(policy, discover_case_ids(tmp_path / "cases"))

    result = privacy.sanitize_text("Use demo_patient with apiKey=SECRET123456 and email test@example.com")

    assert result.redaction_count >= 2
    assert "SECRET123456" not in result.sanitized_text
    assert "demo_patient" not in result.sanitized_text.lower()
    assert "case-id" in result.blocked_reasons
    assert all("demo_patient" not in reason.lower() for reason in result.blocked_reasons)


def test_learning_service_creates_reviewable_draft_and_activates(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)
    config = XDiabetesLearningConfig(
        enabled=True,
        require_human_approval=True,
        auto_activate=False,
        min_observations_to_learn=3,
        min_confidence_to_draft=0.6,
    )
    service = XDiabetesLearningService(workspace=tmp_path, config=config, mode="doctor")

    for idx in range(3):
        result = service.record_turn(
            session_key="cli:direct",
            current_message="Analyze demo_patient and generate a doctor report with safety review",
            tools_used=[
                "xdiabetes_consultation",
                "xdiabetes_safety_check",
                "xdiabetes_generate_report",
            ],
            all_messages=[
                {"role": "tool", "content": "ok"},
                {"role": "assistant", "content": f"turn {idx}"},
            ],
        )
        assert result is not None

    snapshot = service.status_snapshot()
    assert snapshot.observations == 3
    assert snapshot.instincts >= 1
    assert snapshot.drafts >= 1
    observation = service.store.load_observations()[0]
    assert all("demo_patient" not in reason.lower() for reason in observation.blocked_reasons)

    draft, evaluation = service.reviewable_drafts()[0]
    assert evaluation is not None
    assert evaluation.verdict in {"review", "approve", "activate"}
    assert "demo_patient" not in draft.skill_markdown.lower()

    service.approve_draft(draft.draft_id)
    activation_path = service.activate_draft(draft.draft_id)

    assert activation_path.exists()
    assert (tmp_path / "skills" / draft.skill_name / "SKILL.md").exists()
    assert draft.skill_name in service.status_snapshot().active_skills
