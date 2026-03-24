"""Domain-specific exceptions for the X-Diabetes profile."""

from __future__ import annotations


class XDiabetesError(RuntimeError):
    """Base error for all X-Diabetes runtime failures."""


class XDiabetesConfigError(XDiabetesError):
    """Raised when the X-Diabetes configuration is invalid or incomplete."""


class PatientCaseNotFoundError(XDiabetesError):
    """Raised when a requested patient case cannot be located."""


class PatientMemoryError(XDiabetesError):
    """Raised when patient-level longitudinal memory cannot be read or written."""


class KnowledgeBaseError(XDiabetesError):
    """Raised when the local knowledge base is missing or malformed."""


class DTMHAdapterError(XDiabetesError):
    """Raised when a DTMH adapter cannot complete an analysis request."""


class SafetyRuleError(XDiabetesError):
    """Raised when safety rules cannot be loaded or evaluated."""


class LearningError(XDiabetesError):
    """Raised when the continuous-learning pipeline cannot complete."""


class LearningPrivacyError(LearningError):
    """Raised when a learning artifact violates the privacy policy."""
