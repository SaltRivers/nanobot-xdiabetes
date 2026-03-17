# X-Diabetes Future Agent Integration Guide

This MVP intentionally keeps the extension surface small and explicit.

## Option A: add a new native tool

1. Create a tool under `nanobot/agent/tools/xdiabetes/`
2. Register it in `nanobot/x_diabetes/registry.py`
3. Document it in `templates/x_diabetes/TOOLS.md`

This is best when the capability lives in the same codebase.

## Option B: connect an external service over HTTP

1. Expose the capability from your service
2. Create an adapter in `nanobot/x_diabetes/adapters/`
3. Reference it from `build_dtmh_adapter()` or a parallel adapter factory

This is best when the model runs on dedicated GPU infrastructure.

## Option C: connect an external MCP server

nanobot already supports MCP server registration through `tools.mcpServers`.

Recommended pattern:

1. expose the external service as MCP tools
2. register the server in `config.json`
3. call those MCP tools directly from the agent runtime, or wrap them in a future X-Diabetes adapter

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

These live in `nanobot/x_diabetes/schemas.py`.

## New extension points

- Patient-level longitudinal memory: `nanobot/x_diabetes/services/patient_memory_store.py`
- Context enrichment: `nanobot/x_diabetes/services/patient_memory_builder.py`
- HTTP retrieval bridge: `nanobot/x_diabetes/services/rag_api_client.py`
- Retrieval routing/fallback logic: `nanobot/x_diabetes/services/knowledge_router.py`
