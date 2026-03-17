<div align="center">
  <img src="nanobot_logo.png" alt="X-Diabetes" width="320">
  <h1>X-Diabetes</h1>
  <p><strong>A diabetes-oriented clinical agent built on top of nanobot</strong></p>
  <p>
    Doctor-facing consultation · Patient-facing explanation · Patient-level longitudinal memory · Optional RAG API · Future DTMH integration
  </p>
</div>

> [!WARNING]
> **Research prototype only.** X-Diabetes is not a medical device and must not be used as a substitute for licensed clinical judgment, diagnosis, or treatment.

## Overview

X-Diabetes is a disease-specific adaptation of [nanobot](https://github.com/HKUDS/nanobot) for diabetes consultation workflows.

This repository keeps the validated nanobot runtime and adds a minimal, runnable X-Diabetes layer for:

- structured diabetes case analysis
- doctor-facing report generation
- patient-friendly explanation mode
- patient-level longitudinal memory across repeated consultations
- optional external knowledge RAG over HTTP with soft-fail behavior
- a reserved DTMH adapter layer for future model integration

The current implementation is designed as an **MVP system scaffold**: it already runs end-to-end, while leaving explicit extension points for the real DTMH model and additional medical agents.

## Current Status

| Capability | Status |
|---|---|
| X-Diabetes CLI profile | ✅ Implemented |
| Doctor mode | ✅ Implemented |
| Patient mode | ✅ Implemented |
| Structured report generation | ✅ Implemented |
| Patient-level longitudinal memory | ✅ Implemented |
| Optional external RAG API | ✅ Implemented |
| Soft-fail retrieval fallback | ✅ Implemented |
| Future agent integration surface | ✅ Implemented |
| Real DTMH model backend | ⏳ Reserved; default backend is `mock` |
| Skill writer / self-evolving skill acquisition | ⏳ Not included in this MVP |

## What Is Different from Upstream nanobot

Compared with the upstream general-purpose nanobot project, this fork is focused on **X-Diabetes as a vertical medical workflow**.

Key additions in this repository:

- `nanobot xdiabetes onboard`
- `nanobot xdiabetes agent`
- diabetes-oriented tools under `nanobot/agent/tools/xdiabetes/`
- diabetes runtime/services under `nanobot/x_diabetes/`
- patient-level memory persistence under `patient_memory/`
- optional local/external knowledge retrieval routing
- X-Diabetes workspace templates, playbooks, rules, and demo case

## Core Capabilities

### 1. Doctor-facing consultation workflow

The doctor profile can analyze a patient case, retrieve supporting evidence, run the DTMH adapter, perform safety checks, and generate a Markdown report.

### 2. Patient-facing explanation workflow

The patient profile reuses the same case and memory foundation but responds in a more patient-friendly style.

### 3. Patient-level longitudinal memory

X-Diabetes maintains a **patient-specific memory layer** separate from generic chat history.

Default storage path:

```text
~/.nanobot/xdiabetes-workspace/patient_memory/<patient_id>/
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

You can run your own local/domain RAG service and let X-Diabetes call it over HTTP.
If the RAG API is unavailable and `ignoreFailure=true`, the workflow continues instead of failing the whole consultation.

### 5. DTMH integration slot

The DTMH integration layer is already abstracted and supports these backends:

- `mock`
- `python`
- `http`
- `mcp`
- `disabled`

**Current default:** `mock`

This keeps the full consultation pipeline runnable while the real DTMH model is still being trained.

## System Architecture

```text
User / CLI
  -> nanobot xdiabetes agent
  -> AgentLoop
  -> xdiabetes_consultation
  -> PatientStore + PatientMemoryBuilder
  -> KnowledgeRouter (local / api / hybrid)
  -> DTMH adapter (currently mock by default)
  -> SafetyEngine
  -> ReportBuilder
  -> PatientMemoryStore persistence
  -> Markdown report
```

Main tool surface:

- `xdiabetes_patient_context`
- `xdiabetes_patient_memory`
- `xdiabetes_guideline_search`
- `xdiabetes_dtmh`
- `xdiabetes_safety_check`
- `xdiabetes_generate_report`
- `xdiabetes_consultation`

## Repository Structure

```text
repo-root/
├── nanobot/agent/tools/xdiabetes/     # X-Diabetes tool implementations
├── nanobot/x_diabetes/                # schemas, adapters, services, workspace bootstrap
├── nanobot/templates/x_diabetes/      # workspace seed files, demo case, rules, knowledge
├── nanobot/skills/x-diabetes/         # skill/playbook scaffold
├── docs/XDIABETES_QUICKSTART.md
├── docs/XDIABETES_ARCHITECTURE.md
├── docs/XDIABETES_PATIENT_MEMORY.md
├── docs/XDIABETES_RAG_API.md
├── docs/XDIABETES_DTMH_ADAPTER.md
└── docs/XDIABETES_AGENT_INTEGRATION.md
```

## Installation

### Requirements

- Python **3.11+**

### Install from source

```bash
git clone https://github.com/SaltRivers/nanobot-xdiabetes.git
cd nanobot-xdiabetes
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Quick Start

### 1. Initialize the X-Diabetes profile

```bash
nanobot xdiabetes onboard
```

This bootstraps:

- config entry `xDiabetes`
- isolated workspace `~/.nanobot/xdiabetes-workspace`
- demo case `demo_patient`
- seeded knowledge/playbooks/rules/templates
- patient-level memory directory `patient_memory/`

### 2. Configure your LLM provider

Edit `~/.nanobot/config.json`.
Use any provider already supported by nanobot.

A safe generic example is:

```json
{
  "providers": {
    "<providerName>": {
      "apiKey": "YOUR_API_KEY"
    }
  },
  "agents": {
    "defaults": {
      "provider": "<providerName>",
      "model": "<modelName>"
    }
  }
}
```

### 3. Run the doctor-facing agent

```bash
nanobot xdiabetes agent
```

### 4. Run a one-shot doctor consultation

```bash
nanobot xdiabetes agent -m "Analyze demo_patient and generate a doctor report"
```

### 5. Run patient-facing mode

```bash
nanobot xdiabetes agent --mode patient -m "Explain demo_patient in patient-friendly language"
```

## Default Output Locations

The default X-Diabetes workspace is:

```text
~/.nanobot/xdiabetes-workspace/
```

Important subdirectories:

```text
~/.nanobot/xdiabetes-workspace/reports/
~/.nanobot/xdiabetes-workspace/patient_memory/
~/.nanobot/xdiabetes-workspace/cases/
~/.nanobot/xdiabetes-workspace/knowledge/
```

Generated reports are saved under:

```text
~/.nanobot/xdiabetes-workspace/reports/
```

## Configuration Examples

### Enable external RAG API

```json
{
  "xDiabetes": {
    "rag": {
      "backend": "api",
      "apiBaseUrl": "http://127.0.0.1:8008",
      "searchEndpoint": "/search",
      "healthEndpoint": "/health",
      "timeoutS": 3,
      "topK": 3,
      "ignoreFailure": true,
      "fallbackToLocal": false
    }
  }
}
```

### Current DTMH setting for runnable MVP

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "mock"
    }
  }
}
```

### Future HTTP-based DTMH integration

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "http",
      "httpBaseUrl": "http://127.0.0.1:9000",
      "timeoutS": 30
    }
  }
}
```

## Documentation

- [X-Diabetes Quickstart](docs/XDIABETES_QUICKSTART.md)
- [X-Diabetes Architecture](docs/XDIABETES_ARCHITECTURE.md)
- [Patient Longitudinal Memory](docs/XDIABETES_PATIENT_MEMORY.md)
- [External RAG API Contract](docs/XDIABETES_RAG_API.md)
- [DTMH Adapter Notes](docs/XDIABETES_DTMH_ADAPTER.md)
- [Future Agent Integration Guide](docs/XDIABETES_AGENT_INTEGRATION.md)

## How to Extend the System

### Add another native X-Diabetes tool

1. Create the tool in `nanobot/agent/tools/xdiabetes/`
2. Register it in `nanobot/x_diabetes/registry.py`
3. Document it in `nanobot/templates/x_diabetes/TOOLS.md`

### Connect another service over HTTP

1. Expose the service externally
2. Add an adapter in `nanobot/x_diabetes/adapters/`
3. Call it from the X-Diabetes registry or a parallel adapter factory

### Connect another service over MCP

1. Expose the capability as MCP tools
2. Register the server in `config.json`
3. Call those tools directly, or wrap them in an X-Diabetes adapter

Reusable stable contracts live in:

```text
nanobot/x_diabetes/schemas.py
```

## Notes on Clinical Safety

This repository includes workflow-level safety checks and rule-based flags, but these are **engineering safeguards**, not regulatory-grade clinical validation.

Use cases for this repository should be limited to:

- research prototypes
- internal technical validation
- workflow simulation
- future integration testing with validated medical models/services

## Upstream Credit

This project is built on top of the excellent [HKUDS/nanobot](https://github.com/HKUDS/nanobot) runtime.
The X-Diabetes fork keeps nanobot's lightweight agent foundation while specializing it for diabetes consultation workflows.

## License

This repository follows the upstream project license unless explicitly noted otherwise.
