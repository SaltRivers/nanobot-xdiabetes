"""Rule-based safety checks for the X-Diabetes MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nanobot.x_diabetes.errors import SafetyRuleError
from nanobot.x_diabetes.schemas import DTMHResult, PatientCase, SafetyAssessment, SafetyFlag


class SafetyEngine:
    """Evaluate deterministic safety rules over a patient case and DTMH output."""

    def __init__(self, rules_path: Path):
        self._rules_path = rules_path

    def evaluate(self, patient: PatientCase, dtmh_result: DTMHResult) -> SafetyAssessment:
        rules = self._load_rules()
        thresholds = rules.get("thresholds", {})
        flags: list[SafetyFlag] = []
        labs = patient.labs
        vitals = patient.vitals
        demographics = patient.demographics
        cgm = patient.cgm

        hba1c = float(labs.get("hba1c", 0) or 0)
        fpg = float(labs.get("fpg_mmol_l", 0) or 0)
        egfr = float(labs.get("egfr", 0) or 0)
        uacr = float(labs.get("uacr_mg_g", 0) or 0)
        sbp = float(vitals.get("sbp", 0) or 0)
        tir = float(cgm.get("tir_percent", 0) or 0)
        pregnant = bool(demographics.get("pregnant", False))

        if hba1c >= float(thresholds.get("urgent_hba1c", 10.0)) or fpg >= float(thresholds.get("urgent_fpg_mmol_l", 16.7)):
            flags.append(
                SafetyFlag(
                    severity="critical",
                    code="SEVERE_HYPERGLYCEMIA",
                    message="Glycemic markers are in a range that requires urgent clinical review.",
                    recommendation="Escalate immediately for clinician assessment and urgent management planning.",
                )
            )

        if egfr and egfr < float(thresholds.get("kidney_egfr_critical", 30)):
            flags.append(
                SafetyFlag(
                    severity="critical",
                    code="ADVANCED_KIDNEY_DYSFUNCTION",
                    message="Renal function is in a high-risk range.",
                    recommendation="Review medication suitability, nephrology input, and renal-protective strategy.",
                )
            )
        elif egfr and egfr < float(thresholds.get("kidney_egfr_low", 45)):
            flags.append(
                SafetyFlag(
                    severity="warning",
                    code="KIDNEY_CAUTION",
                    message="Renal function is reduced and should constrain treatment choices.",
                    recommendation="Re-check renal labs and review dose adjustments before intensifying therapy.",
                )
            )

        if uacr >= float(thresholds.get("uacr_high_mg_g", 30)):
            flags.append(
                SafetyFlag(
                    severity="warning",
                    code="ALBUMINURIA_SIGNAL",
                    message="Albuminuria is present and suggests renal complication risk.",
                    recommendation="Confirm kidney disease staging and ensure renal-protective follow-up.",
                )
            )

        if sbp >= float(thresholds.get("bp_systolic_high", 160)):
            flags.append(
                SafetyFlag(
                    severity="warning",
                    code="SEVERE_HYPERTENSION_SIGNAL",
                    message="Systolic blood pressure is markedly elevated.",
                    recommendation="Treat as a high-priority cardiovascular risk issue and confirm repeat measurements.",
                )
            )

        if tir and tir < float(thresholds.get("tir_low_percent", 50)):
            flags.append(
                SafetyFlag(
                    severity="warning",
                    code="LOW_TIME_IN_RANGE",
                    message="CGM time-in-range is low and suggests unstable glycemic control.",
                    recommendation="Review CGM pattern, adherence, and short-interval follow-up.",
                )
            )

        if pregnant:
            flags.append(
                SafetyFlag(
                    severity="info",
                    code="PREGNANCY_CONTEXT",
                    message="Pregnancy context requires extra caution when interpreting recommendations.",
                    recommendation="Validate any recommendation against gestational-diabetes guidance and obstetric care.",
                )
            )

        if dtmh_result.backend == "mock":
            flags.append(
                SafetyFlag(
                    severity="info",
                    code="MOCK_DTMH_BACKEND",
                    message="The current DTMH result comes from the placeholder mock backend.",
                    recommendation="Treat the structured result as workflow scaffolding only; do not rely on it as a validated model output.",
                )
            )

        overall = "pass"
        if any(flag.severity == "critical" for flag in flags):
            overall = "escalate"
        elif any(flag.severity == "warning" for flag in flags):
            overall = "review"

        return SafetyAssessment(
            overall_status=overall,
            flags=flags,
            disclaimer=str(rules.get("disclaimer", "AI output must be reviewed by a clinician before clinical use.")),
        )

    def _load_rules(self) -> dict[str, Any]:
        if not self._rules_path.exists():
            raise SafetyRuleError(
                f"Safety rules file not found: {self._rules_path}. Run xdiabetes onboard first."
            )
        try:
            payload = json.loads(self._rules_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SafetyRuleError(f"Safety rules file is not valid JSON: {self._rules_path}") from exc

        if not isinstance(payload, dict):
            raise SafetyRuleError("Safety rules file must contain a JSON object.")
        return payload
