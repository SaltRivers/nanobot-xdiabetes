# X-Diabetes Continuous Learning Evaluation

Each learned draft passes through three gates:

1. **Instinct gate**
   - repeated evidence
   - acceptable contradiction/error rate
2. **Draft gate**
   - privacy check
   - required sections
   - conflict check against existing skills
   - synthetic evaluation fixtures
3. **Activation gate**
   - final draft re-check before copying into `workspace/skills/`

## Verdicts

- `drop`
- `revise`
- `review`
- `approve`
- `activate`

## Synthetic fixtures

Synthetic fixtures live under:

```text
learning/evals/synthetic_skill_eval_cases.json
```

They are designed to validate skill structure and safety markers **without** using real patient data.
