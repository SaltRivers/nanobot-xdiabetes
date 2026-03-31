# X-Diabetes

X-Diabetes is a diabetes-focused clinical workflow agent for structured case review, patient-facing explanation, longitudinal patient memory, optional external knowledge retrieval, and future DTMH integration.

> [!WARNING]
> **Research prototype only.** X-Diabetes is not a medical device and must not be used as a substitute for licensed clinical judgment, diagnosis, or treatment.

## Overview

This repository provides a runnable X-Diabetes workflow layer with:

- doctor-facing diabetes case analysis
- patient-facing explanation mode
- patient-level longitudinal memory across repeated consultations
- optional external RAG retrieval over HTTP with soft-fail behavior
- privacy-gated continuous learning for workflow skills
- a reserved DTMH adapter layer for future model integration

## Current Status

| Capability | Status |
|---|---|
| X-Diabetes CLI | ✅ Implemented |
| Doctor mode | ✅ Implemented |
| Patient mode | ✅ Implemented |
| Structured report generation | ✅ Implemented |
| Patient-level longitudinal memory | ✅ Implemented |
| Optional external RAG API | ✅ Implemented |
| Soft-fail retrieval fallback | ✅ Implemented |
| Privacy-gated continuous learning | ✅ Implemented |
| Draft / approval / activation flow | ✅ Implemented |
| Real DTMH backend | ⏳ Reserved; default backend is `mock` |
| Post-activation monitoring / rollback | ✅ Implemented |

## Core Capabilities

### 1. Doctor-facing consultation workflow

The doctor profile can analyze a patient case, retrieve supporting evidence, run the DTMH adapter, perform safety checks, and generate a Markdown report.

### 2. Patient-facing explanation workflow

The patient profile reuses the same case and memory foundation but responds in more patient-friendly language.

### 3. Patient-level longitudinal memory

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

### 4. Optional external RAG API

You can connect a local or domain-specific retrieval service over HTTP. When the API is unavailable and `ignoreFailure=true`, the workflow continues instead of failing the whole consultation.

### 5. DTMH integration slot

Supported backend values:

- `mock`
- `python`
- `http`
- `mcp`
- `disabled`

**Current default:** `mock`

### 6. Privacy-gated continuous learning

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
- demo case `demo_patient`
- seeded knowledge, rules, and templates
- patient-level memory directory `patient_memory/`

### Configure your provider

Edit `~/.x-diabetes/config.json` and set a valid provider key.

### Run the doctor-facing workflow

```bash
x-diabetes agent
```

### Run a one-shot doctor consultation

```bash
x-diabetes agent -m "Analyze demo_patient and generate a doctor report"
```

### Run patient-facing mode

```bash
x-diabetes agent --mode patient -m "Explain demo_patient in patient-friendly language"
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
<package_root>/templates/workspace_seed/      # workspace seed files, demo case, rules, knowledge
<package_root>/skills/x-diabetes/         # workflow playbook scaffold
```

## Documentation

- [X-Diabetes Quickstart](docs/X_DIABETES_QUICKSTART.md)
- [X-Diabetes Architecture](docs/X_DIABETES_ARCHITECTURE.md)
- [Patient Longitudinal Memory](docs/X_DIABETES_PATIENT_MEMORY.md)
- [External RAG API Contract](docs/X_DIABETES_RAG_API.md)
- [DTMH Adapter Notes](docs/X_DIABETES_DTMH_ADAPTER.md)
- [Future Agent Integration Guide](docs/X_DIABETES_AGENT_INTEGRATION.md)
- [Continuous Learning Overview](docs/X_DIABETES_CONTINUOUS_LEARNING.md)
- [Continuous Learning Privacy Guardrails](docs/X_DIABETES_CONTINUOUS_LEARNING_PRIVACY.md)
- [Continuous Learning Evaluation and Activation](docs/X_DIABETES_CONTINUOUS_LEARNING_EVAL.md)

## Clinical Safety Note

This repository includes workflow-level safety checks and rule-based flags, but these are engineering safeguards rather than regulatory-grade clinical validation.

Recommended usage:

- research prototypes
- internal technical validation
- workflow simulation
- future integration testing with validated medical systems

## License

MIT, unless explicitly noted otherwise.
