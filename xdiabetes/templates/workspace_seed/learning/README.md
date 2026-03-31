# X-Diabetes continuous learning

This directory stores **privacy-filtered** learning artifacts.

## Safety defaults

- Learning is disabled by default.
- Only sanitized workflow metadata should be stored here.
- Draft skills must pass evaluation before approval or activation.
- Learned skills must never contain patient-specific identifiers or report text.

## Layout

- `observations/` — sanitized turn observations
- `instincts/` — repeated workflow patterns distilled from observations
- `drafts/` — generated skill drafts awaiting review
- `evaluations/` — instinct/draft/activation evaluation records
- `approved/` — approval audit trail
- `rejected/` — rejection audit trail
- `rollback/` — previous live skill versions kept for rollback
- `state/` — monitoring state for activated learned skills
- `policies/` — workspace-local learning policy
- `evals/` — synthetic evaluation fixtures
