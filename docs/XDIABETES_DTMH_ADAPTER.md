# X-Diabetes DTMH Adapter Guide

The adapter contract lives in:

- `<package_root>/clinical/schemas.py` → `DTMHRequest`, `DTMHResult`
- `<package_root>/clinical/adapters/base.py` → `DTMHAdapter`

## Supported backend values

- `mock` → current default, runnable placeholder
- `python` → future local callable bridge
- `http` → future remote service
- `mcp` → reserved for future MCP-native integration
- `disabled` → explicit off switch

## Python backend

Config example:

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "python",
      "pythonEntrypoint": "my_dtmh.entry:run_dtmh"
    }
  }
}
```

Expected callable signature:

```python
def run_dtmh(request_dict: dict) -> dict:
    ...
```

The return value must match `DTMHResult`.

## HTTP backend

### Mode A: native X-Diabetes contract

Use this when your remote service already accepts `DTMHRequest` and returns
`DTMHResult`.

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "http",
      "httpBaseUrl": "http://127.0.0.1:8080",
      "httpEndpoint": "/analyze",
      "httpRequestFormat": "xdiabetes"
    }
  }
}
```

Expected endpoint:

- `POST /analyze`
- request body: `DTMHRequest`
- response body: `DTMHResult`

### Mode B: direct DT-CAN / DTMH `/predict` integration

Use this when your DTMH service is the DT-CAN-style API under
`DTMH/examples/api_service.py`.

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "http",
      "httpBaseUrl": "http://127.0.0.1:8000",
      "httpEndpoint": "/predict",
      "httpRequestFormat": "dtcan_predict",
      "checkpointPath": "/ABS/PATH/TO/checkpoints/deepdr_ehr_text/best.pt",
      "configPath": "/ABS/PATH/TO/DTMH/src/configs/deepdr_ehr_text.yaml",
      "encodeRaw": true,
      "outputFormat": "probabilities",
      "returnLatents": false
    }
  }
}
```

In this mode, X-Diabetes will:

1. convert `PatientCase` into DT-CAN raw modalities:
   - `ehr`: `[gender, age, height, weight, bmi, sbp, dbp, triglyceride, hdl, ldl, HbA1c, diabetes_duration, smoke]`
   - `text`: built from notes / fundus summary / complications / medications / history
2. call your DTMH HTTP API
3. normalize the HTTP response back into `DTMHResult`

### Currently supported DT-CAN response alignment

The adapter now recognizes these response shapes:

- full `DTMHResult`
- DT-CAN-style:

```json
{
  "predictions": {
    "system": {
      "diabetes": 0.78
    }
  },
  "metadata": {
    "inference_time_ms": 123.4
  }
}
```

- minimal probability-only payloads such as:

```json
{
  "diabetes_probability": 0.78
}
```

At the moment, only the diabetes probability is required. Future additional
fields from your service can be added without breaking the runtime because the
runtime schema is forward-compatible.

### Optional patient-level overrides

If a specific case already has a DTMH-ready payload, place it in the case JSON
under `metadata.dtmh`:

```json
{
  "patient_id": "demo_patient",
  "metadata": {
    "dtmh": {
      "data": {
        "ehr": [0, 46, 0, 0, 29.4, 148, 92, 2.1, 0, 3.2, 8.7, 4, 0],
        "text": ["Demo note"]
      },
      "config": {
        "encode_raw": true
      }
    }
  }
}
```

You can also override the full HTTP body with `metadata.dtmh.requestBody`.

If you want X-Diabetes to auto-build the DT-CAN payload but keep only certain
modalities, you can use:

```json
{
  "metadata": {
    "dtmh": {
      "modalities": ["ehr"]
    }
  }
}
```

This is useful when the local checkpoint can run with missing modalities, but
you do not want to load an optional text/image encoder for a quick demo.
