# X-Diabetes DTMH Adapter Guide

The adapter contract lives in:

- `nanobot/x_diabetes/schemas.py` → `DTMHRequest`, `DTMHResult`
- `nanobot/x_diabetes/adapters/base.py` → `DTMHAdapter`

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

Config example:

```json
{
  "xDiabetes": {
    "dtmh": {
      "backend": "http",
      "httpBaseUrl": "http://127.0.0.1:8080"
    }
  }
}
```

Expected endpoint:

- `POST /analyze`
- request body: `DTMHRequest`
- response body: `DTMHResult`
