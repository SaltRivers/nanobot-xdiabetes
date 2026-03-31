# X-Diabetes Runtime Profile

Current operating mode: **{{MODE}}**

## Expected behavior by mode

- **doctor**: prioritize structured assessment, evidence, safety flags, and recommended next checks.
- **patient**: prioritize plain-language explanation, urgency cues, and follow-up actions.

## DTMH backend

This workspace uses the DTMH HTTP backend by default. The model runs on a remote server
and is called via HTTP API (e.g. `/predict_csv`). No local deep-learning libraries are needed.

If continuous learning is enabled, only privacy-filtered workflow metadata should
be stored, and learned skills should be reviewed before activation.
