"""Mock DTMH adapter for the runnable MVP.

This is intentionally heuristic and **not** a medical model. It exists so the
X-Diabetes profile can run end-to-end while the real DTMH is still training.
"""

from __future__ import annotations

from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.schemas import DTMHRequest, DTMHResult


class MockDTMHAdapter(DTMHAdapter):
    """Simple rule-based stand-in for the real DTMH service."""

    @property
    def backend_name(self) -> str:
        return "mock"

    def analyze(self, request: DTMHRequest) -> DTMHResult:
        patient = request.patient
        labs = patient.labs
        vitals = patient.vitals
        cgm = patient.cgm
        imaging = patient.imaging
        history = patient.history
        demographics = patient.demographics

        hba1c = float(labs.get("hba1c", 0) or 0)
        fpg = float(labs.get("fpg_mmol_l", 0) or 0)
        egfr = float(labs.get("egfr", 0) or 0)
        uacr = float(labs.get("uacr_mg_g", 0) or 0)
        ldl = float(labs.get("ldl_mmol_l", 0) or 0)
        trig = float(labs.get("triglycerides_mmol_l", 0) or 0)
        c_peptide = float(labs.get("c_peptide_ng_ml", 0) or 0)
        gad_positive = bool(labs.get("gad_antibody_positive", False))
        bmi = float(demographics.get("bmi", 0) or 0)
        sbp = float(vitals.get("sbp", 0) or 0)
        tir = float(cgm.get("tir_percent", 0) or 0)
        fundus_text = str(imaging.get("fundus_summary", "")).lower()
        prior_stroke = bool(history.get("stroke_history", False))
        age = int(demographics.get("age", 0) or 0)

        glycemia_label = "stable"
        glycemia_score = 0.22
        if hba1c >= 10 or fpg >= 16.7:
            glycemia_label = "poor_control"
            glycemia_score = 0.86
        elif hba1c >= 8.5 or fpg >= 10:
            glycemia_label = "suboptimal_control"
            glycemia_score = 0.68
        elif hba1c >= 7 or tir < 70:
            glycemia_label = "needs_optimization"
            glycemia_score = 0.51

        lada_score = 0.12
        subtype = "type2_likely"
        if gad_positive or (age >= 30 and c_peptide and c_peptide < 1.0):
            lada_score = 0.73
            subtype = "lada_possible"
        elif bmi >= 28 and trig >= 1.7:
            lada_score = 0.08
            subtype = "insulin_resistant_type2_pattern"

        kidney_score = 0.18
        kidney_label = "low_risk"
        if egfr and egfr < 45 or uacr >= 300:
            kidney_score = 0.84
            kidney_label = "high_risk"
        elif egfr and egfr < 60 or uacr >= 30:
            kidney_score = 0.58
            kidney_label = "moderate_risk"

        eye_score = 0.20
        eye_label = "low_risk"
        if "retinopathy" in fundus_text or "microaneurysm" in fundus_text:
            eye_score = 0.66
            eye_label = "moderate_risk"

        heart_score = 0.21
        heart_label = "low_risk"
        if sbp >= 160 or ldl >= 3.4:
            heart_score = 0.73
            heart_label = "high_risk"
        elif sbp >= 140 or ldl >= 2.6:
            heart_score = 0.55
            heart_label = "moderate_risk"

        brain_score = 0.14
        brain_label = "low_risk"
        if prior_stroke or sbp >= 160:
            brain_score = 0.62
            brain_label = "moderate_risk"

        liver_score = 0.16
        liver_label = "low_risk"
        if bmi >= 30 or trig >= 2.3:
            liver_score = 0.49
            liver_label = "metabolic_stress"

        islet_score = 0.34 if subtype == "lada_possible" else 0.46
        islet_label = "autoimmune_signal" if subtype == "lada_possible" else "insulin_resistance_pattern"

        next_steps = [
            "Correlate the mock digital-twin summary with the treating clinician's judgement.",
            "Validate glycemic control with repeat HbA1c / CGM trend review.",
        ]
        if subtype == "lada_possible":
            next_steps.append("Consider autoimmune diabetes work-up and specialist review.")
        if kidney_score >= 0.58:
            next_steps.append("Review kidney protection strategy and repeat renal assessment.")
        if eye_score >= 0.66:
            next_steps.append("Schedule ophthalmology / retinal follow-up if not already arranged.")

        summary = (
            f"Mock DTMH backend suggests {glycemia_label.replace('_', ' ')} with a {subtype.replace('_', ' ')} "
            f"pattern. The most notable complication signals are kidney={kidney_label}, eye={eye_label}, "
            f"heart={heart_label}."
        )

        return DTMHResult(
            patient_id=patient.patient_id,
            backend=self.backend_name,
            model_version="mock-dtmh-v0",
            summary=summary,
            organ_states={
                "liver": {"state": liver_label, "score": liver_score},
                "heart": {"state": heart_label, "score": heart_score},
                "brain": {"state": brain_label, "score": brain_score},
                "kidney": {"state": kidney_label, "score": kidney_score},
                "eye": {"state": eye_label, "score": eye_score},
                "pancreatic_islet": {"state": islet_label, "score": islet_score},
            },
            risk_profile={
                "glycemic_control": {"label": glycemia_label, "score": glycemia_score},
                "lada_suspicion": {"label": subtype, "score": lada_score},
                "kidney_complication": {"label": kidney_label, "score": kidney_score},
                "retinopathy_signal": {"label": eye_label, "score": eye_score},
                "cardiovascular_signal": {"label": heart_label, "score": heart_score},
            },
            recommended_next_steps=next_steps,
            uncertainty={
                "level": "high",
                "reason": "Mock adapter uses deterministic heuristics because the real DTMH is still training.",
            },
            warnings=[
                "This result is generated by a placeholder mock backend and must not be treated as a validated model output.",
            ],
        )
