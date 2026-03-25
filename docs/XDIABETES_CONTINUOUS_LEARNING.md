# X-Diabetes Continuous Learning

X-Diabetes can learn workflow skills from repeated usage patterns, but the feature is disabled by default.

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
x-diabetes learning enable
x-diabetes learning status
x-diabetes learning review
x-diabetes learning eval <draft_id>
x-diabetes learning approve <draft_id>
x-diabetes learning activate <draft_id>
```

## Runtime override

```bash
x-diabetes agent --learning
x-diabetes agent --no-learning
```

## Lifecycle

1. collect sanitized observations
2. derive instincts
3. generate draft skills
4. evaluate draft quality and privacy
5. approve + activate
6. monitor for contradictions and rollback if needed
