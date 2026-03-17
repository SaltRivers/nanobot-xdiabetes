"""HTTP adapter for a future external DTMH service."""

from __future__ import annotations

import httpx

from nanobot.x_diabetes.adapters.base import DTMHAdapter
from nanobot.x_diabetes.errors import DTMHAdapterError
from nanobot.x_diabetes.schemas import DTMHRequest, DTMHResult


class HTTPDTMHAdapter(DTMHAdapter):
    """Call a remote DTMH service over HTTP."""

    def __init__(self, base_url: str, timeout_s: int = 30):
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        if not self._base_url:
            raise DTMHAdapterError("httpBaseUrl is required when dtmh.backend='http'.")

    @property
    def backend_name(self) -> str:
        return "http"

    def analyze(self, request: DTMHRequest) -> DTMHResult:
        endpoint = f"{self._base_url}/analyze"
        try:
            response = httpx.post(
                endpoint,
                json=request.model_dump(mode="json"),
                timeout=self._timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - depends on external service
            raise DTMHAdapterError(f"HTTP DTMH request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - depends on external service
            raise DTMHAdapterError("HTTP DTMH response was not valid JSON.") from exc

        return DTMHResult.model_validate(payload)
