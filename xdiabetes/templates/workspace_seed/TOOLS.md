# X-Diabetes Tool Notes

## Primary tool

- `xdiabetes_dtmh` is the preferred first tool for diabetes inference requests.
  - For direct prediction: provide `cohort_dir` and `patient_id` to call the remote DTMH HTTP service.
  - Optionally override `checkpoint_path`, `config_path`, or `output_format` per call.

## Supporting tools

- `xdiabetes_patient_context`: inspect a normalized local patient case (when available)
- `xdiabetes_patient_memory`: inspect patient-level longitudinal workflow memory
- `xdiabetes_guideline_search`: retrieve evidence from the configured local/API RAG backend
- `xdiabetes_safety_check`: apply deterministic safety rules to DTMH results

## Optional workflow tools

- `xdiabetes_generate_report`: build and save a Markdown report (use only when explicitly requested)
- `xdiabetes_consultation`: full end-to-end orchestration (use only when the user wants a complete workflow artifact)

## Learned skills

- Learned skills are generated under `learning/drafts/` first
- They must pass privacy and safety evaluation before activation into `skills/`
- Review them with `x-diabetes learning review`
