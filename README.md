# X-Diabetes

X-Diabetes is a diabetes-focused agent that calls a remote DTMH model for structured diabetes inference, with support for patient longitudinal memory, optional external knowledge retrieval, and privacy-gated continuous learning.

> [!WARNING]
> **Research prototype only.** X-Diabetes is not a medical device and must not be used as a substitute for licensed clinical judgment, diagnosis, or treatment.

## Overview

This repository provides a runnable X-Diabetes agent with:

- DTMH HTTP inference as the primary execution path
- patient-level longitudinal memory across repeated consultations
- optional external RAG retrieval over HTTP with soft-fail behavior
- privacy-gated continuous learning for workflow skills
- doctor-facing and patient-facing output modes

## Current Status

| Capability | Status |
|---|---|
| X-Diabetes CLI | ✅ Implemented |
| DTMH HTTP backend | ✅ Implemented (default) |
| Doctor mode | ✅ Implemented |
| Patient mode | ✅ Implemented |
| Patient-level longitudinal memory | ✅ Implemented |
| Optional external RAG API | ✅ Implemented |
| Soft-fail retrieval fallback | ✅ Implemented |
| Privacy-gated continuous learning | ✅ Implemented |
| Draft / approval / activation flow | ✅ Implemented |
| Post-activation monitoring / rollback | ✅ Implemented |

## Core Capabilities

### 1. DTMH HTTP inference

The agent calls a remote DTMH model via HTTP API (default endpoint: `http://localhost:8000/predict_csv`). The model runs on a remote server — no local deep-learning libraries are needed.

**Request format:**

```json
{
  "cohort_dir": "Dataset/private_fundus",
  "patient_id": 4,
  "checkpoint_path": "checkpoints/deepdr_ehr_text/best.pt",
  "config_path": "src/configs/deepdr_ehr_text.yaml",
  "output_format": "probabilities"
}
```

**Supported backends:**

- `http` (default)
- `mock`
- `python`
- `mcp`
- `disabled`

### 2. Patient-level longitudinal memory

Default storage path:

```text
~/.x-diabetes/x-diabetes-workspace/patient_memory/<patient_id>/
```

Typical artifacts include:

- `profile.json`
- `summary.md`
- `latest_snapshot.json`
- `timeline.jsonl`
- `reports_index.jsonl`
- `encounters/*.json`
- `risk_assessments/*.json`

### 3. Optional external RAG API

You can connect a local or domain-specific retrieval service over HTTP. When the API is unavailable and `ignoreFailure=true`, the workflow continues instead of failing.

### 4. Privacy-gated continuous learning

X-Diabetes can optionally learn workflow skills from repeated usage patterns.

Important constraints:

- disabled by default
- stores sanitized workflow metadata instead of raw patient content
- generates draft skills before activation
- requires evaluation before approval/activation
- supports monitoring and rollback after activation

## Quick Start

### Install from source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### Initialize the profile

```bash
x-diabetes onboard
```

This bootstraps:

- config entry `xDiabetes`
- isolated workspace `~/.x-diabetes/x-diabetes-workspace`
- seeded knowledge, rules, and templates
- patient-level memory directory `patient_memory/`

### Configure your provider

Edit `~/.x-diabetes/config.json` and set a valid provider key.

### Configure DTMH HTTP endpoint (optional)

The default is `http://localhost:8000/predict_csv`. To override:

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "http",
      "httpBaseUrl": "http://localhost:8000",
      "httpEndpoint": "/predict_csv",
      "checkpointPath": "checkpoints/deepdr_ehr_text/best.pt",
      "configPath": "src/configs/deepdr_ehr_text.yaml",
      "outputFormat": "probabilities"
    }
  }
}
```

### Run the agent

```bash
x-diabetes agent
```

### Run a one-shot query

```bash
x-diabetes agent -m "Check whether patient 4 in Dataset/private_fundus has diabetes"
```

### Run patient-facing mode

```bash
x-diabetes agent --mode patient -m "Explain the diabetes risk for patient 4"
```

## Default Output Locations

```text
~/.x-diabetes/x-diabetes-workspace/
~/.x-diabetes/x-diabetes-workspace/reports/
~/.x-diabetes/x-diabetes-workspace/patient_memory/
~/.x-diabetes/x-diabetes-workspace/cases/
~/.x-diabetes/x-diabetes-workspace/knowledge/
~/.x-diabetes/x-diabetes-workspace/learning/
~/.x-diabetes/x-diabetes-workspace/skills/
```

Learned-skill artifacts are saved under:

```text
~/.x-diabetes/x-diabetes-workspace/learning/observations/
~/.x-diabetes/x-diabetes-workspace/learning/instincts/
~/.x-diabetes/x-diabetes-workspace/learning/drafts/
~/.x-diabetes/x-diabetes-workspace/learning/evaluations/
~/.x-diabetes/x-diabetes-workspace/learning/approved/
~/.x-diabetes/x-diabetes-workspace/learning/rejected/
~/.x-diabetes/x-diabetes-workspace/learning/rollback/
~/.x-diabetes/x-diabetes-workspace/skills/<learned-skill>/
```

## Continuous Learning Commands

```bash
x-diabetes agent --learning
x-diabetes learning status
x-diabetes learning review
x-diabetes learning eval <draft_id>
x-diabetes learning approve <draft_id>
x-diabetes learning activate <draft_id>
x-diabetes learning rollback <skill_name>
```

## Repository Layout

The most relevant code lives under the package root:

```text
<package_root>/agent/tools/diabetes/     # X-Diabetes tool implementations
<package_root>/clinical/                # schemas, adapters, services, learning, workspace bootstrap
<package_root>/clinical/learning/       # observation, draft, eval, activation, monitoring pipeline
<package_root>/templates/workspace_seed/      # workspace seed files, rules, knowledge
<package_root>/skills/x-diabetes/         # workflow playbook scaffold
```

## Documentation

- [X-Diabetes Quickstart](docs/XDIABETES_QUICKSTART.md)
- [X-Diabetes Architecture](docs/XDIABETES_ARCHITECTURE.md)
- [Patient Longitudinal Memory](docs/XDIABETES_PATIENT_MEMORY.md)
- [External RAG API Contract](docs/XDIABETES_RAG_API.md)
- [DTMH Adapter Notes](docs/XDIABETES_DTMH_ADAPTER.md)
- [Future Agent Integration Guide](docs/XDIABETES_AGENT_INTEGRATION.md)
- [Continuous Learning Overview](docs/XDIABETES_CONTINUOUS_LEARNING.md)
- [Continuous Learning Privacy Guardrails](docs/XDIABETES_CONTINUOUS_LEARNING_PRIVACY.md)
- [Continuous Learning Evaluation and Activation](docs/XDIABETES_CONTINUOUS_LEARNING_EVAL.md)

## Clinical Safety Note

This repository includes workflow-level safety checks and rule-based flags, but these are engineering safeguards rather than regulatory-grade clinical validation.

Recommended usage:

- research prototypes
- internal technical validation
- workflow simulation
- future integration testing with validated medical systems

## License

MIT, unless explicitly noted otherwise.
