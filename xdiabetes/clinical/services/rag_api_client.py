"""HTTP client for an external/local X-Diabetes RAG service."""

from __future__ import annotations

import httpx

from xdiabetes.clinical.errors import KnowledgeBaseError
from xdiabetes.clinical.schemas import KnowledgeHit


class RAGAPIClient:
    """Thin client for a JSON over HTTP retrieval service."""

    def __init__(
        self,
        *,
        base_url: str,
        search_endpoint: str = "/search",
        health_endpoint: str = "/health",
        timeout_s: int = 3,
        headers: dict[str, str] | None = None,
    ):
        normalized_base = base_url.rstrip("/")
        if not normalized_base:
            raise KnowledgeBaseError("xDiabetes.rag.apiBaseUrl is required when rag.backend uses the API mode.")
        self._base_url = normalized_base
        self._search_endpoint = self._normalize_endpoint(search_endpoint)
        self._health_endpoint = self._normalize_endpoint(health_endpoint)
        self._timeout_s = timeout_s
        self._headers = headers or {}

    @property
    def search_url(self) -> str:
        """Return the fully-qualified search URL."""
        return f"{self._base_url}{self._search_endpoint}"

    def healthcheck(self) -> bool:
        """Best-effort health check for the external retrieval service."""
        response = httpx.get(
            f"{self._base_url}{self._health_endpoint}",
            headers=self._headers,
            timeout=self._timeout_s,
        )
        response.raise_for_status()
        return True

    def search(
        self,
        *,
        query: str,
        patient_id: str = "",
        task: str = "general",
        audience: str = "doctor",
        top_k: int = 3,
        filters: dict | None = None,
    ) -> list[KnowledgeHit]:
        """Submit a retrieval request and normalize the response into KnowledgeHit objects."""
        response = httpx.post(
            self.search_url,
            json={
                "query": query,
                "patient_id": patient_id,
                "task": task,
                "audience": audience,
                "top_k": top_k,
                "filters": filters or {},
            },
            headers=self._headers,
            timeout=self._timeout_s,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise KnowledgeBaseError("RAG API returned a non-JSON response.") from exc

        items = self._extract_items(payload)
        return [KnowledgeHit.model_validate(item) for item in items]

    def _extract_items(self, payload: object) -> list[dict]:
        """Accept a few common API response wrappers to keep integration flexible."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("hits", "results", "items", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        raise KnowledgeBaseError(
            "RAG API response must be a JSON list or an object containing hits/results/items/data."
        )

    def _normalize_endpoint(self, endpoint: str) -> str:
        endpoint = endpoint.strip() or "/"
        return endpoint if endpoint.startswith("/") else f"/{endpoint}"
