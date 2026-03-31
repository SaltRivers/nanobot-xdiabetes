---
description: X-Diabetes playbook for structured diabetes inference via DTMH.
---

# X-Diabetes Skill

Use this skill when the user wants diabetes-focused analysis or prediction.

## Default workflow

1. For diabetes-analysis requests, extract from the user query:
   - `cohort_dir` (the dataset directory, e.g. `Dataset/private_fundus`)
   - `patient_id` (the patient index or identifier)
   - any explicit overrides for `checkpoint_path`, `config_path`, or `output_format`
2. Call `xdiabetes_dtmh` with those parameters. This sends the request to the remote DTMH HTTP service.
3. Use `xdiabetes_patient_memory` only if prior longitudinal context would help interpretation.
4. Use `xdiabetes_guideline_search` if the user needs supporting clinical evidence.
5. Use `xdiabetes_safety_check` when safety validation is requested.
6. Use `xdiabetes_generate_report` only when the user explicitly asks for a saved report artifact.
7. Prefer doctor-facing outputs unless the user explicitly asks for patient-facing language.

## Example

User: "Check whether patient 4 in Dataset/private_fundus has diabetes"

Tool call:
```
xdiabetes_dtmh(cohort_dir="Dataset/private_fundus", patient_id=4)
```

## Workspace conventions

- Local cases (optional) live in `cases/`
- Knowledge files live in `knowledge/`
- Reports are written to `reports/`
- Patient longitudinal workflow artifacts live in `patient_memory/`
- Safety rules live in `rules/default_rules.json`
