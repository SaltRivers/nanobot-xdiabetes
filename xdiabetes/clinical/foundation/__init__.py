"""Foundation Agent workflow for X-Diabetes.

The Foundation Agent orchestrates clinical reasoning through a structured workflow:
1. Query decomposition and guideline-based planning
2. Data preparation and validation
3. DTMH capability orchestration
4. Clinical interpretation with evidence augmentation
5. Reflective decision-making
6. Clinical report generation

This module transforms X-Diabetes from a tool-calling agent into a
guideline-grounded clinical decision support system.
"""

from xdiabetes.clinical.foundation.schemas import (
    ClinicalInterpretation,
    ClinicalTaskPlan,
    DTMHExecutionPlan,
    DataPreparationResult,
    FoundationTrace,
    GuidelinePlan,
    ReflectionDecision,
)

__all__ = [
    "ClinicalTaskPlan",
    "GuidelinePlan",
    "DataPreparationResult",
    "DTMHExecutionPlan",
    "ClinicalInterpretation",
    "ReflectionDecision",
    "FoundationTrace",
]
