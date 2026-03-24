# X-Diabetes Patient Longitudinal Memory

## Goal

X-Diabetes keeps a patient-level memory layer separate from generic chat history so the runtime can accumulate workflow history, risk snapshots, and reports across repeated consultations.

## Storage layout

Patient memory lives under the X-Diabetes workspace:

```text
~/.x-diabetes/x-diabetes-workspace/patient_memory/<patient_id>/
```

Each patient directory contains:

- `profile.json` — latest durable demographics snapshot
- `summary.md` — human-readable longitudinal summary
- `latest_snapshot.json` — latest workflow-derived patient state
- `timeline.jsonl` — append-only timeline of workflow events
- `reports_index.jsonl` — append-only report pointers
- `encounters/*.json` — structured encounter records
- `risk_assessments/*.json` — structured risk snapshots

## Runtime behavior

### Read path

Before analysis, the runtime:

1. loads the patient case JSON
2. loads patient memory artifacts
3. injects a compact longitudinal summary and recent events into `PatientContext`

### Write path

After consultation/report generation, the runtime:

1. updates `latest_snapshot.json`
2. writes an encounter record
3. writes a structured risk record
4. appends a timeline event
5. appends a report index entry when a report is saved
6. rebuilds `summary.md`

## Configuration

```json
{
  "xDiabetes": {
    "memory": {
      "enabled": true,
      "patientMemoryDir": "patient_memory",
      "timelineMaxRead": 10,
      "summaryFilename": "summary.md",
      "writeEncounter": true,
      "writeRiskAssessment": true,
      "writeReportIndex": true
    }
  }
}
```
