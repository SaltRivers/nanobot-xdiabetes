# X-Diabetes Future Agent Integration Guide

This MVP intentionally keeps the extension surface small and explicit.

## Option A: add a new native tool

1. Create a tool under `<package_root>/agent/tools/diabetes/`
2. Register it in `<package_root>/clinical/registry.py`
3. Document it in `templates/workspace_seed/TOOLS.md`

## Option B: connect an external service over HTTP

1. Expose the capability from your service
2. Create an adapter in `<package_root>/clinical/adapters/`
3. Reference it from `build_dtmh_adapter()` or a parallel adapter factory

## Option C: connect an external MCP server

The runtime already supports MCP server registration through `tools.mcpServers`.

Recommended pattern:

1. expose the external service as MCP tools
2. register the server in `config.json`
3. call those MCP tools directly from the runtime, or wrap them in a future X-Diabetes adapter

## Stable contracts to reuse

- `PatientCase`
- `PatientContext`
- `PatientLongitudinalSnapshot`
- `EncounterRecord`
- `KnowledgeRetrievalMetadata`
- `DTMHRequest`
- `DTMHResult`
- `SafetyAssessment`
- `ReportArtifact`

These live in `<package_root>/clinical/schemas.py`.

## New extension points

- Patient-level longitudinal memory: `<package_root>/clinical/services/patient_memory_store.py`
- Context enrichment: `<package_root>/clinical/services/patient_memory_builder.py`
- HTTP retrieval bridge: `<package_root>/clinical/services/rag_api_client.py`
- Retrieval routing/fallback logic: `<package_root>/clinical/services/knowledge_router.py`
