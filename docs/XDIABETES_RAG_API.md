# X-Diabetes RAG API Integration

## Goal

X-Diabetes can call an external/local retrieval service over HTTP. If that service is offline,
times out, or returns invalid data, the workflow can continue without RAG evidence.

## Configuration

```json
{
  "xDiabetes": {
    "rag": {
      "backend": "api",
      "apiBaseUrl": "http://127.0.0.1:8008",
      "searchEndpoint": "/search",
      "healthEndpoint": "/health",
      "timeoutS": 3,
      "topK": 5,
      "ignoreFailure": true,
      "fallbackToLocal": false,
      "headers": {}
    }
  }
}
```

Supported backend values:

- `local`
- `api`
- `hybrid`
- `disabled`

## Expected endpoints

### Health

```http
GET /health
```

### Search

```http
POST /search
Content-Type: application/json
```

Example request body:

```json
{
  "query": "diabetic kidney disease follow-up",
  "patient_id": "demo_patient",
  "task": "complication",
  "audience": "doctor",
  "top_k": 5,
  "filters": {}
}
```

## Response contract

The API may return either:

1. a JSON list of knowledge hits; or
2. a JSON object containing one of: `hits`, `results`, `items`, `data`

Each hit should match the `KnowledgeHit` schema used by X-Diabetes.

## Failure behavior

When `ignoreFailure=true`, these failures do **not** stop the workflow:

- connection failure
- timeout
- HTTP error
- invalid JSON / invalid shape

Instead, X-Diabetes records retrieval metadata and continues with zero evidence results.

## Optional local fallback

If you want API-first retrieval with a deterministic local fallback, set:

```json
{
  "xDiabetes": {
    "rag": {
      "backend": "api",
      "fallbackToLocal": true
    }
  }
}
```
