"""Policy loading for X-Diabetes continuous learning."""

from __future__ import annotations

import json
from pathlib import Path

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.clinical.learning.schemas import LearningPolicy

DEFAULT_BLOCKED_REGEXES = [
    r"(?i)\b(patient[_ -]?id|mrn|medical record|身份证|病历号)\b",
    r"(?i)\b(patient[_ -]?name|full[_ -]?name|姓名)\b",
    r"(?i)\b(api[_-]?key|token|secret|password|authorization|bearer)\b",
    r"(?i)\b(email|phone|address|dob|date of birth)\b",
]
DEFAULT_BLOCKED_FIELD_NAMES = [
    "patient_id",
    "patient_name",
    "full_name",
    "phone",
    "email",
    "address",
    "mrn",
    "medical_record_number",
    "身份证",
    "病历号",
    "api_key",
    "token",
    "secret",
    "password",
]
DEFAULT_REQUIRED_SECTIONS = [
    "# ",
    "## Overview",
    "## When to use",
    "## Learned workflow",
    "## Safety boundaries",
]
DEFAULT_SAFETY_KEYWORDS = [
    "patient-specific",
    "not medical advice",
    "clinician",
    "privacy",
]


def build_default_policy(config: XDiabetesLearningConfig) -> LearningPolicy:
    """Build a default policy from runtime configuration."""

    return LearningPolicy(
        blocked_regexes=list(DEFAULT_BLOCKED_REGEXES),
        blocked_field_names=list(DEFAULT_BLOCKED_FIELD_NAMES),
        required_skill_sections=list(DEFAULT_REQUIRED_SECTIONS),
        safety_keywords=list(DEFAULT_SAFETY_KEYWORDS),
        min_observations_to_learn=config.min_observations_to_learn,
        min_confidence_to_draft=config.min_confidence_to_draft,
        max_similarity_before_conflict=config.max_similarity_before_conflict,
    )


def load_learning_policy(path: Path, config: XDiabetesLearningConfig) -> LearningPolicy:
    """Load the workspace learning policy, falling back to safe defaults."""

    policy = build_default_policy(config)
    if not path.exists():
        return policy

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return policy

    try:
        loaded = LearningPolicy.model_validate(payload)
    except Exception:
        return policy

    merged = policy.model_dump(mode="python")
    merged.update({k: v for k, v in loaded.model_dump(mode="python").items() if v not in (None, [], {})})
    return LearningPolicy.model_validate(merged)
