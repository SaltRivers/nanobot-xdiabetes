# X-Diabetes Tool Notes

## Primary workflow tool

- `xdiabetes_consultation` is the preferred first tool for end-to-end case analysis.

## Lower-level tools

- `xdiabetes_patient_context`: inspect the normalized case
- `xdiabetes_patient_memory`: inspect patient-level longitudinal workflow memory
- `xdiabetes_dtmh`: inspect the current DTMH backend output
- `xdiabetes_guideline_search`: retrieve evidence from the configured local/API RAG backend
- `xdiabetes_safety_check`: apply deterministic safety rules
- `xdiabetes_generate_report`: build and save a Markdown report

## Important limitation

If the DTMH backend is `mock`, its output is only a placeholder for workflow integration.

## Learned skills

- Learned skills are generated under `learning/drafts/` first
- They must pass privacy and safety evaluation before activation into `skills/`
- Review them with `nanobot xdiabetes learning review`
