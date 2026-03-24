"""Observation-to-instinct analysis for X-Diabetes continuous learning."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import UTC, datetime

from xdiabetes.config.schema import XDiabetesLearningConfig
from xdiabetes.x_diabetes.learning.schemas import (
    LearningInstinct,
    LearningObservation,
    LearningPolicy,
)


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "workflow"


def _build_action(representative: LearningObservation) -> str:
    tool_sequence = representative.tool_sequence_signature or "xdiabetes_consultation"
    if representative.domain == "communication" or "patient_explanation" in representative.intent_labels:
        return "Prefer calm, patient-friendly explanations while keeping advice within clinician-reviewed boundaries."
    if representative.domain == "reporting":
        return "Generate structured Markdown reports after the core consultation workflow completes successfully."
    if representative.domain == "safety":
        return "Run a safety review before finalizing recommendations or report output."
    if representative.tool_names:
        return f"Prefer the workflow sequence: {tool_sequence}."
    return "Start with the end-to-end consultation flow before using lower-level tools."


def _build_title(representative: LearningObservation) -> str:
    bits = [representative.mode.title()]
    if representative.task != "general":
        bits.append(representative.task.replace("_", " ").title())
    bits.append(representative.domain.title())
    bits.append("Workflow")
    return " ".join(bits)


def _build_trigger(representative: LearningObservation) -> str:
    if representative.task != "general":
        return f"when handling {representative.task} requests in {representative.mode} mode"
    if "patient_explanation" in representative.intent_labels:
        return "when explaining diabetes findings to patients"
    if representative.report_requested:
        return f"when generating {representative.mode}-facing diabetes reports"
    return f"when running X-Diabetes consultations in {representative.mode} mode"


def analyze_observations(
    observations: list[LearningObservation],
    policy: LearningPolicy,
    config: XDiabetesLearningConfig,
) -> list[LearningInstinct]:
    """Group sanitized observations into reusable instincts."""

    grouped: dict[str, list[LearningObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.pattern_key].append(observation)

    instincts: list[LearningInstinct] = []
    for pattern_key, items in grouped.items():
        items = sorted(items, key=lambda item: item.created_at)
        representative = items[-1]
        evidence_count = len(items)
        error_rate = sum(1 for item in items if item.error_count > 0) / evidence_count
        correction_rate = sum(1 for item in items if item.correction_signal) / evidence_count
        confidence = 0.3 + 0.12 * max(evidence_count - 1, 0)
        if representative.safety_tool_used:
            confidence += 0.08
        if representative.report_requested:
            confidence += 0.04
        confidence -= error_rate * 0.15
        confidence -= correction_rate * 0.18
        confidence = max(0.05, min(0.95, round(confidence, 3)))
        status = (
            "strong"
            if evidence_count >= policy.min_observations_to_learn and confidence >= config.min_confidence_to_draft
            else "tentative"
        )
        instinct_seed = f"{representative.mode}:{representative.domain}:{representative.task}:{pattern_key}"
        instinct_id = f"{_slugify(representative.domain)}-{_slugify(representative.task)}-{hashlib.sha1(instinct_seed.encode('utf-8')).hexdigest()[:8]}"
        instincts.append(
            LearningInstinct(
                instinct_id=instinct_id,
                created_at=items[0].created_at,
                updated_at=datetime.now(UTC),
                title=_build_title(representative),
                trigger=_build_trigger(representative),
                action=_build_action(representative),
                rationale=(
                    f"Observed {evidence_count} times with tool sequence "
                    f"'{representative.tool_sequence_signature or 'xdiabetes_consultation'}'."
                ),
                domain=representative.domain,
                mode=representative.mode,
                task=representative.task,
                pattern_key=pattern_key,
                confidence=confidence,
                evidence_count=evidence_count,
                evidence_observation_ids=[item.observation_id for item in items],
                correction_rate=round(correction_rate, 3),
                error_rate=round(error_rate, 3),
                report_requested=representative.report_requested,
                safety_tool_used=representative.safety_tool_used,
                status=status,
            )
        )

    return sorted(instincts, key=lambda item: (-item.confidence, -item.evidence_count, item.instinct_id))
