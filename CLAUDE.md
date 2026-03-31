# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

X-Diabetes is a diabetes-focused clinical workflow agent for structured case review, patient-facing explanation, longitudinal patient memory, optional external knowledge retrieval, and future DTMH integration.

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
x-diabetes agent -m "message"        # one-shot consultation
x-diabetes agent --mode patient      # patient-facing mode
x-diabetes agent --learning          # enable continuous learning
x-diabetes learning status          # check learning status
x-diabetes learning review          # review pending drafts
x-diabetes learning eval <draft_id> # evaluate a draft
x-diabetes learning approve <draft_id>
x-diabetes learning activate <draft_id>
x-diabetes learning rollback <skill_name>
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
- `xdiabetes.agent.tools` - Tool registry and diabetes-specific tools
- `xdiabetes.clinical` - Clinical workflow layer (schemas, adapters, services)
- `xdiabetes.channels` - 20+ messaging channel integrations (Telegram, Slack, Discord, WhatsApp, DingTalk, Feishu, QQ, WeCom, Matrix, Email, etc.)

### Runtime Path
```
User/CLI
  -> AgentLoop
  -> xdiabetes_consultation tool
  -> PatientStore + PatientMemoryBuilder
  -> KnowledgeRouter (local/API/hybrid)
  -> DTMH adapter (default: mock)
  -> SafetyEngine + ReportBuilder
  -> PatientMemoryStore persistence
  -> Markdown report
```

### DTMH Adapters
Supported backend values: `mock`, `python`, `http`, `mcp`, `disabled`
- Default is `mock` (reserved slot for real model integration)
- Configured in `~/.x-diabetes/config.json` under `xDiabetes.dtmhBackend`

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
| `xdiabetes/agent/loop.py` | Agent orchestration runtime |
| `xdiabetes/agent/tools/diabetes/` | Diabetes-specific tools |
| `xdiabetes/clinical/` | Schemas, adapters, services, learning |
| `xdiabetes/cli/app.py` | CLI entry point (Typer) |
| `xdiabetes/templates/workspace_seed/` | Demo case, knowledge base, rules |
| `docs/` | Architecture and integration guides |

## Technology Stack

- Python 3.11+ with hatch/hatchling
- TypeScript/Node.js 20+ (WhatsApp bridge)
- Typer (CLI), Pydantic (validation), litellm (LLM integration)
- pytest with asyncio for testing
- ruff for linting (py311, line-length 100)