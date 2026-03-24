# X-Diabetes Architecture Notes

This implementation keeps the runtime surface compact and adds a diabetes-focused workflow layer.

## Reused runtime components

- `AgentLoop` → orchestration runtime
- `ToolRegistry` → tool dispatch layer
- `Session + Memory` → longitudinal conversation context
- `MCP` → future external service / agent integration path

## X-Diabetes-specific layer

- `<package_root>/x_diabetes/` → schemas, adapters, workspace bootstrap, services
- `<package_root>/agent/tools/xdiabetes/` → diabetes-focused tools
- `<package_root>/templates/x_diabetes/` → isolated workspace seed data
- `<package_root>/skills/x-diabetes/` → workflow playbook
- `patient_memory/` within the workspace → patient-level longitudinal memory
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

The DTMH backend is intentionally mocked until the real model is ready.
