"""Turn-level observation collection for X-Diabetes learning."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

from xdiabetes.clinical.learning.privacy import PrivacyFilter
from xdiabetes.clinical.learning.schemas import LearningObservation

_CORRECTION_RE = re.compile(r"(?i)\b(no|instead|correct|revise|change|don't|do not|不是|不要|改成|修正)\b")
_DIABETES_RE = re.compile(r"(?i)\b(diabetes|glycemic|hba1c|glucose|insulin|cgm|retina|kidney|uacr|egfr)\b")
_TASK_HINTS: dict[str, str] = {
    "screen": "screening",
    "follow": "followup",
    "subtyp": "subtyping",
    "complic": "complication",
    "manag": "management",
    "risk": "complication",
}


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _extract_task(message: str) -> str:
    lowered = message.lower()
    for hint, task in _TASK_HINTS.items():
        if hint in lowered:
            return task
    return "general"


def _extract_message_features(message: str, mode: str) -> tuple[list[str], list[str], bool]:
    lowered = message.lower()
    features = [f"mode:{mode}"]
    intents: list[str] = []
    report_requested = False

    if "report" in lowered or "markdown" in lowered:
        features.append("report_requested")
        intents.append("doctor_report")
        report_requested = True
    if "patient" in lowered or mode == "patient":
        features.append("patient_friendly")
        intents.append("patient_explanation")
    if "doctor" in lowered or mode == "doctor":
        features.append("doctor_facing")
    if "safety" in lowered or "risk" in lowered:
        features.append("safety_sensitive")
        intents.append("safety_review")
    if "explain" in lowered:
        features.append("explanation")
    if "consult" in lowered or "analy" in lowered:
        features.append("consultation")
        intents.append("consultation")

    task = _extract_task(message)
    features.append(f"task:{task}")
    intents.append(f"task:{task}")
    return _ordered_unique(features), _ordered_unique(intents), report_requested


def _count_tool_errors(messages: list[dict[str, Any]]) -> int:
    count = 0
    for message in messages:
        if message.get("role") != "tool":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.startswith("Error"):
            count += 1
    return count


def _classify_domain(tool_names: list[str], message_features: list[str], safety_tool_used: bool) -> str:
    if safety_tool_used:
        return "safety"
    if any(item.startswith("task:") and item != "task:general" for item in message_features):
        return "workflow"
    if any(item == "patient_friendly" for item in message_features):
        return "communication"
    if "xdiabetes_generate_report" in tool_names or "report_requested" in message_features:
        return "reporting"
    return "workflow"


def collect_turn_observation(
    *,
    session_key: str,
    mode: str,
    current_message: str,
    tools_used: list[str],
    all_messages: list[dict[str, Any]],
    privacy_filter: PrivacyFilter,
) -> LearningObservation | None:
    """Create one sanitized observation from a finished X-Diabetes turn.

    The observation stores only workflow metadata, derived intent labels, and a
    hashed pattern key. Raw patient content is never written to disk.
    """

    if not tools_used and not _DIABETES_RE.search(current_message or ""):
        return None

    scan = privacy_filter.sanitize_text(current_message)
    message_features, intents, report_requested = _extract_message_features(scan.sanitized_text, mode)
    tool_names = _ordered_unique(tools_used)
    safety_tool_used = "xdiabetes_safety_check" in tool_names or "safety_sensitive" in message_features
    domain = _classify_domain(tool_names, message_features, safety_tool_used)
    correction_signal = bool(_CORRECTION_RE.search(current_message or ""))
    task = _extract_task(scan.sanitized_text)
    sequence = ">".join(tool_names)
    pattern_seed = "|".join(
        [
            f"mode:{mode}",
            f"domain:{domain}",
            f"task:{task}",
            f"report:{int(report_requested)}",
            f"safety:{int(safety_tool_used)}",
            f"tools:{sequence}",
            f"intents:{','.join(intents)}",
        ]
    )
    pattern_hash = hashlib.sha1(pattern_seed.encode("utf-8")).hexdigest()[:10]
    pattern_key = f"{domain}:{task}:{pattern_hash}"

    return LearningObservation(
        observation_id=hashlib.sha1(f"{session_key}:{pattern_seed}:{len(all_messages)}".encode("utf-8")).hexdigest()[:16],
        session_key=session_key,
        mode="patient" if mode == "patient" else "doctor",
        domain=domain,
        task=task,
        tool_names=tool_names,
        tool_sequence_signature=sequence,
        intent_labels=intents,
        message_features=message_features,
        pattern_key=pattern_key,
        report_requested=report_requested,
        safety_tool_used=safety_tool_used,
        error_count=_count_tool_errors(all_messages),
        correction_signal=correction_signal,
        redaction_count=scan.redaction_count,
        blocked_reasons=scan.blocked_reasons,
    )
