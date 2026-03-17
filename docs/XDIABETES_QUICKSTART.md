# X-Diabetes Quickstart

## 1. Initialize the profile

```bash
nanobot xdiabetes onboard
```

This creates:

- config entry `xDiabetes`
- isolated workspace `~/.nanobot/xdiabetes-workspace`
- demo case `demo_patient`
- local knowledge seed files
- default safety rules
- patient-level longitudinal memory directory `patient_memory/`

## 2. Configure your LLM provider

Edit `~/.nanobot/config.json` and set a valid provider key, for example under `providers.openrouter.apiKey`.

## 3. Run the doctor-facing profile

```bash
nanobot xdiabetes agent
```

Or send a one-shot message:

```bash
nanobot xdiabetes agent -m "Analyze demo_patient and generate a doctor report"
```

## 4. Run patient-facing mode

```bash
nanobot xdiabetes agent --mode patient -m "Explain demo_patient in patient-friendly language"
```

## 5. Important note about DTMH

The real DTMH is still training in this repository state.
The default runnable backend is:

```json
"xDiabetes": {
  "dtmh": {
    "backend": "mock"
  }
}
```

That backend is a workflow placeholder only.

## 6. Optional patient longitudinal memory

Every consultation now writes patient-level workflow memory under:

```text
~/.nanobot/xdiabetes-workspace/patient_memory/<patient_id>/
```

See `docs/XDIABETES_PATIENT_MEMORY.md` for details.

## 7. Optional external RAG API

If you run your own local RAG service, configure:

```json
{
  "xDiabetes": {
    "rag": {
      "backend": "api",
      "apiBaseUrl": "http://127.0.0.1:8008",
      "ignoreFailure": true
    }
  }
}
```

When the API is unavailable, X-Diabetes continues without RAG evidence instead of failing the full workflow.
See `docs/XDIABETES_RAG_API.md` for the API contract.
