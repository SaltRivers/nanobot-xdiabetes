# X-Diabetes Architecture Notes

This implementation keeps nanobot's validated runtime and adds a minimal diabetes-focused layer.

## Reused nanobot components

- `AgentLoop` → Foundation Agent runtime
- `ToolRegistry` → medical tool mesh
- `Session + Memory` → longitudinal conversation memory
- `MCP` → future external service / agent integration path

## Added X-Diabetes layer

- `nanobot/x_diabetes/` → schemas, adapters, workspace bootstrap, services
- `nanobot/agent/tools/xdiabetes/` → diabetes-focused tools
- `nanobot/templates/x_diabetes/` → isolated workspace seed data
- `nanobot/skills/x-diabetes/` → workflow playbook
- `patient_memory/` within the workspace → patient-level longitudinal workflow memory
- optional external RAG API → HTTP retrieval with soft-fail behavior

## Current runnable path

```text
User/CLI
  -> AgentLoop
  -> xdiabetes_consultation
  -> PatientStore + PatientMemoryBuilder
  -> KnowledgeRouter (local/API/hybrid)
  -> mock DTMH + SafetyEngine + ReportBuilder
  -> PatientMemoryStore persistence
  -> Markdown report
```

## Current limitation

The DTMH backend is intentionally mocked until the real model finishes training.
