# X-Diabetes Continuous Learning

X-Diabetes can learn **workflow skills** from repeated usage patterns, but the feature is **disabled by default**.

## What it learns

- tool ordering patterns
- doctor/patient mode workflow preferences
- reporting and safety-review habits

## What it does not learn

- raw patient case content
- patient identifiers
- report bodies
- secrets or API credentials

## Main commands

```bash
nanobot xdiabetes learning enable
nanobot xdiabetes learning status
nanobot xdiabetes learning review
nanobot xdiabetes learning eval <draft_id>
nanobot xdiabetes learning approve <draft_id>
nanobot xdiabetes learning activate <draft_id>
```

## Runtime override

```bash
nanobot xdiabetes agent --learning
nanobot xdiabetes agent --no-learning
```

## Lifecycle

1. collect sanitized observations
2. derive instincts
3. generate draft skills
4. evaluate draft quality and privacy
5. approve + activate
6. monitor for contradictions and rollback if needed
