# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

X-Diabetes is a diabetes-focused agent that calls a remote DTMH model for structured diabetes inference, with support for patient longitudinal memory, optional external knowledge retrieval, and privacy-gated continuous learning.

**Important:** This is a research prototype only. Not a medical device and must not be used as a substitute for licensed clinical judgment, diagnosis, or treatment.

## Common Commands

### Development Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -U pip
pip install -e .           # install with dev dependencies
pip install -e ".[dev]"    # full dev dependencies including test tools
```

### Testing
```bash
python -m pytest tests/ -v              # run all tests
python -m pytest tests/path/to/test.py -v  # run specific test file
python -m pytest tests/ -v -k "pattern"   # run tests matching pattern
```

### Linting
```bash
ruff check .           # check all files
ruff check --fix .    # auto-fix issues
```

### CLI Commands
```bash
x-diabetes onboard                    # initialize profile and workspace
x-diabetes agent                     # run interactive agent
x-diabetes agent -m "message"        # one-shot query
x-diabetes agent --mode patient      # patient-facing mode
x-diabetes agent --learning          # enable continuous learning
x-diabetes learning status          # check learning status
x-diabetes learning review          # review pending drafts
x-diabetes learning eval <draft_id> # evaluate a draft
x-diabetes learning approve <draft_id>
x-diabetes learning activate <draft_id>
x-diabetes learning rollback <skill_name>
```

### Example Query
```bash
x-diabetes agent -m "Check whether patient 4 in Dataset/private_fundus has diabetes"
```

### Bridge (WhatsApp)
```bash
cd bridge && npm install
npm run build  # compiles TypeScript to dist/
npm start      # runs the bridge
```

## Architecture

### Core Runtime Components
- `xdiabetes.agent.loop.AgentLoop` - Main orchestration runtime
- `xdiabetes.agent.tools.diabetes.dtmh_adapter` - Primary DTMH inference tool
- `xdiabetes.clinical.adapters.http` - HTTP adapter for remote DTMH service
- `xdiabetes.clinical` - Clinical workflow layer (schemas, adapters, services)
- `xdiabetes.channels` - 20+ messaging channel integrations (Telegram, Slack, Discord, WhatsApp, DingTalk, Feishu, QQ, WeCom, Matrix, Email, etc.)

### Runtime Path
```
User/CLI
  -> AgentLoop
  -> xdiabetes_dtmh tool (primary)
  -> HTTPDTMHAdapter
  -> POST http://localhost:8000/predict_csv
  -> DTMHResult normalization
  -> Optional: PatientMemoryStore, SafetyEngine, ReportBuilder
```

### DTMH HTTP Integration
The agent calls a remote DTMH model via HTTP API. The model runs on a remote server — no local deep-learning libraries are needed.

**Default endpoint:** `http://localhost:8000/predict_csv`

**Request format (dtcan_predict_csv):**
```json
{
  "cohort_dir": "Dataset/private_fundus",
  "patient_id": 4,
  "checkpoint_path": "checkpoints/deepdr_ehr_text/best.pt",
  "config_path": "src/configs/deepdr_ehr_text.yaml",
  "output_format": "probabilities"
}
```

**Supported backends:** `http` (default), `mock`, `python`, `mcp`, `disabled`

Configured in `~/.x-diabetes/config.json` under `xDiabetes.dtmh`

### Data Storage
- Configuration: `~/.x-diabetes/config.json`
- Workspace: `~/.x-diabetes/x-diabetes-workspace/`
- Patient memory: `~/.x-diabetes/x-diabetes-workspace/patient_memory/<patient_id>/`
- Reports: `~/.x-diabetes/x-diabetes-workspace/reports/`

### Continuous Learning Artifacts
- Observations: `learning/observations/`
- Draft skills: `learning/instincts/`
- Pending review: `learning/drafts/`
- Approved skills: `learning/approved/`
- Active skills: `skills/<skill_name>/`
- Rollback history: `learning/rollback/`

## Key Files

| Path | Purpose |
|------|---------|
| `xdiabetes/agent/tools/diabetes/dtmh_adapter.py` | Primary DTMH inference tool |
| `xdiabetes/clinical/adapters/http.py` | HTTP adapter for remote DTMH service |
| `xdiabetes/clinical/registry.py` | Tool registration (DTMH first) |
| `xdiabetes/agent/loop.py` | Agent orchestration runtime |
| `xdiabetes/clinical/` | Schemas, adapters, services, learning |
| `xdiabetes/config/schema.py` | Config definitions (DTMH defaults) |
| `xdiabetes/cli/app.py` | CLI entry point (Typer) |
| `xdiabetes/skills/x-diabetes/SKILL.md` | Workflow playbook |
| `xdiabetes/templates/workspace_seed/` | Workspace seed files, rules, knowledge |
| `docs/` | Architecture and integration guides |

## Technology Stack

- Python 3.11+ with hatch/hatchling
- TypeScript/Node.js 20+ (WhatsApp bridge)
- Typer (CLI), Pydantic (validation), litellm (LLM integration)
- pytest with asyncio for testing
- ruff for linting (py311, line-length 100)