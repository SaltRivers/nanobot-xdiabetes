"""Privacy helpers for X-Diabetes continuous learning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from xdiabetes.x_diabetes.learning.schemas import LearningPolicy

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization|bearer|credentials?)"
    r"([\s:=\"']+)"
    r"([A-Za-z0-9_\-/.+=]{6,})"
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s\-()]{7,}\d)")
_LONG_NUMBER_RE = re.compile(r"\b\d{8,}\b")


@dataclass(slots=True)
class PrivacyScanResult:
    """Outcome of scanning one piece of text."""

    sanitized_text: str
    redaction_count: int
    blocked_reasons: list[str]


class PrivacyFilter:
    """Filter raw text down to privacy-safe learning metadata."""

    def __init__(self, policy: LearningPolicy, case_ids: set[str] | None = None):
        self._policy = policy
        self._case_ids = {item.lower() for item in (case_ids or set()) if item}
        self._blocked_regexes = [re.compile(pattern) for pattern in policy.blocked_regexes]

    def sanitize_text(self, text: str) -> PrivacyScanResult:
        """Redact common secrets and identifiers from arbitrary text."""

        sanitized = text or ""
        redactions = 0
        blocked: list[str] = []

        for regex, replacement in (
            (_SECRET_RE, r"\1\2[REDACTED]"),
            (_EMAIL_RE, "[REDACTED_EMAIL]"),
            (_PHONE_RE, "[REDACTED_PHONE]"),
            (_LONG_NUMBER_RE, "[REDACTED_ID]"),
        ):
            sanitized, count = regex.subn(replacement, sanitized)
            redactions += count

        lowered = sanitized.lower()
        for case_id in self._case_ids:
            if case_id and case_id in lowered:
                blocked.append("case-id")
                sanitized = re.sub(re.escape(case_id), "[REDACTED_CASE]", sanitized, flags=re.IGNORECASE)
                redactions += 1

        for regex in self._blocked_regexes:
            if regex.search(lowered):
                blocked.append(f"pattern:{regex.pattern}")

        return PrivacyScanResult(
            sanitized_text=sanitized,
            redaction_count=redactions,
            blocked_reasons=sorted(set(blocked)),
        )

    def find_skill_issues(self, text: str) -> list[str]:
        """Return policy violations that make a learned skill unsafe to save."""

        issues: list[str] = []
        scan = self.sanitize_text(text)
        if scan.redaction_count:
            issues.append("draft skill contains content that required redaction")
        issues.extend(scan.blocked_reasons)

        lowered = text.lower()
        for field_name in self._policy.blocked_field_names:
            if field_name.lower() in lowered:
                issues.append(f"field-name:{field_name}")

        return sorted(set(issues))


def discover_case_ids(cases_dir: Path) -> set[str]:
    """Best-effort discovery of case identifiers to avoid leaking them into skills."""

    if not cases_dir.exists():
        return set()
    return {path.stem for path in cases_dir.glob("*.json")}
