---
description: Built-in clinical workflow playbook for structured diabetes case analysis.
---

# Clinical Workflow Playbook

Use this skill when the user wants the runtime's built-in diabetes-focused clinical workflow.

## Default workflow

1. Start with `xdiabetes_consultation` for an end-to-end MVP analysis.
2. If deeper inspection is needed, use the lower-level tools in this order:
   - `xdiabetes_patient_context`
   - `xdiabetes_patient_memory`
   - `xdiabetes_dtmh`
   - `xdiabetes_guideline_search`
   - `xdiabetes_safety_check`
   - `xdiabetes_generate_report`
3. When discussing findings, clearly state whether the current DTMH backend is `mock`.
4. Prefer doctor-facing outputs unless the user explicitly asks for patient-facing language.
5. Never present mock-DTMH output as validated medical advice.

## Workspace conventions

- Cases live in `cases/`
- Knowledge files live in `knowledge/`
- Reports are written to `reports/`
- Patient longitudinal workflow artifacts live in `patient_memory/`
- Safety rules live in `rules/default_rules.json`

## Current repository status

- The real DTMH model is still training.
- The default runnable workflow uses a placeholder mock adapter.
- The mock adapter is for system integration testing only.
