# X-Diabetes Continuous Learning Privacy

## Default posture

- disabled by default
- strict privacy enabled by default
- human approval required by default
- auto-activation disabled by default

## Privacy controls

The learning pipeline redacts or blocks:

- patient identifiers (`patient_id`, MRN, case IDs)
- emails, phone numbers, long numeric identifiers
- API keys, tokens, passwords, authorization strings
- raw report text and case-specific details from reusable skills

## Safe boundary

The system stores **workflow metadata**, not patient narratives.

Examples of safe learning:
- "doctor-mode consultations often run safety review before report generation"
- "patient-mode explanations prefer calm language"

Examples of unsafe learning:
- any patient-specific timeline, report excerpt, or diagnosis text
- copied structured case JSON
- prompts containing identifiers or credentials
