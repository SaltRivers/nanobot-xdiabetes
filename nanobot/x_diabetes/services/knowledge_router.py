"""Knowledge routing with soft-fail API retrieval support."""

from __future__ import annotations

from time import perf_counter

import httpx

from nanobot.x_diabetes.errors import KnowledgeBaseError
from nanobot.x_diabetes.schemas import (
    KnowledgeHit,
    KnowledgeRetrievalMetadata,
    KnowledgeRetrievalResult,
)
from nanobot.x_diabetes.services.knowledge_store import KnowledgeStore
from nanobot.x_diabetes.services.rag_api_client import RAGAPIClient


class KnowledgeRouter:
    """Route retrieval requests across local and API backends."""

    def __init__(
        self,
        *,
        backend: str = "local",
        local_store: KnowledgeStore | None = None,
        api_client: RAGAPIClient | None = None,
        ignore_failure: bool = True,
        fallback_to_local: bool = False,
        default_top_k: int = 3,
    ):
        self._backend = backend
        self._local_store = local_store
        self._api_client = api_client
        self._ignore_failure = ignore_failure
        self._fallback_to_local = fallback_to_local
        self._default_top_k = default_top_k

    def search(
        self,
        *,
        query: str,
        patient_id: str = "",
        task: str = "general",
        audience: str = "doctor",
        limit: int | None = None,
        filters: dict | None = None,
    ) -> KnowledgeRetrievalResult:
        """Retrieve evidence with optional API soft-fail behavior."""
        query = query.strip()
        limit = limit or self._default_top_k
        if not query:
            return KnowledgeRetrievalResult(
                metadata=KnowledgeRetrievalMetadata(
                    backend_requested=self._backend,
                    backend_used="none",
                    status="skipped",
                    result_count=0,
                )
            )

        if self._backend == "disabled":
            return KnowledgeRetrievalResult(
                metadata=KnowledgeRetrievalMetadata(
                    backend_requested="disabled",
                    backend_used="disabled",
                    status="skipped",
                    result_count=0,
                )
            )
        if self._backend == "local":
            return self._search_local(query=query, limit=limit)
        if self._backend == "api":
            return self._search_api(
                query=query,
                patient_id=patient_id,
                task=task,
                audience=audience,
                limit=limit,
                filters=filters,
            )
        if self._backend == "hybrid":
            return self._search_hybrid(
                query=query,
                patient_id=patient_id,
                task=task,
                audience=audience,
                limit=limit,
                filters=filters,
            )
        raise KnowledgeBaseError(f"Unsupported X-Diabetes RAG backend: {self._backend}")

    def _search_local(self, *, query: str, limit: int) -> KnowledgeRetrievalResult:
        start = perf_counter()
        if self._local_store is None:
            return self._soft_failure("local_unconfigured", "Local knowledge backend is not configured.", start)
        try:
            hits = self._local_store.search(query=query, limit=limit)
        except Exception as exc:
            return self._maybe_raise_or_soft_fail("local_error", str(exc), start)
        return KnowledgeRetrievalResult(
            hits=hits,
            metadata=KnowledgeRetrievalMetadata(
                backend_requested=self._backend,
                backend_used="local",
                status="ok" if hits else "empty",
                latency_ms=int((perf_counter() - start) * 1000),
                result_count=len(hits),
            ),
        )

    def _search_api(
        self,
        *,
        query: str,
        patient_id: str,
        task: str,
        audience: str,
        limit: int,
        filters: dict | None,
    ) -> KnowledgeRetrievalResult:
        start = perf_counter()
        if self._api_client is None:
            return self._maybe_api_fallback_or_soft_fail(
                query=query,
                limit=limit,
                start=start,
                status="api_unconfigured",
                warning="RAG API backend is enabled but apiBaseUrl is not configured.",
            )
        try:
            hits = self._api_client.search(
                query=query,
                patient_id=patient_id,
                task=task,
                audience=audience,
                top_k=limit,
                filters=filters,
            )
        except httpx.TimeoutException:
            return self._maybe_api_fallback_or_soft_fail(
                query=query,
                limit=limit,
                start=start,
                status="api_timeout",
                warning="RAG API request timed out; continuing without external evidence.",
            )
        except httpx.ConnectError:
            return self._maybe_api_fallback_or_soft_fail(
                query=query,
                limit=limit,
                start=start,
                status="api_connection_error",
                warning="RAG API connection failed; continuing without external evidence.",
            )
        except httpx.HTTPError as exc:
            return self._maybe_api_fallback_or_soft_fail(
                query=query,
                limit=limit,
                start=start,
                status="api_http_error",
                warning=f"RAG API returned an HTTP error: {exc}",
            )
        except Exception as exc:
            return self._maybe_api_fallback_or_soft_fail(
                query=query,
                limit=limit,
                start=start,
                status="api_invalid_response",
                warning=f"RAG API returned an invalid response: {exc}",
            )

        return KnowledgeRetrievalResult(
            hits=hits,
            metadata=KnowledgeRetrievalMetadata(
                backend_requested=self._backend,
                backend_used="api",
                status="ok" if hits else "empty",
                latency_ms=int((perf_counter() - start) * 1000),
                result_count=len(hits),
            ),
        )

    def _search_hybrid(
        self,
        *,
        query: str,
        patient_id: str,
        task: str,
        audience: str,
        limit: int,
        filters: dict | None,
    ) -> KnowledgeRetrievalResult:
        """Combine API and local retrieval while keeping API failures soft."""
        api_result = self._search_api(
            query=query,
            patient_id=patient_id,
            task=task,
            audience=audience,
            limit=limit,
            filters=filters,
        )
        local_result = self._search_local(query=query, limit=limit)
        merged_hits = self._merge_hits(api_result.hits, local_result.hits)[:limit]

        warning_parts = [part for part in (api_result.metadata.warning, local_result.metadata.warning) if part]
        status = "ok" if merged_hits else api_result.metadata.status
        if local_result.metadata.status == "ok" and api_result.metadata.status not in {"ok", "empty"}:
            status = "hybrid_local_only"
        elif api_result.metadata.status == "ok" and local_result.metadata.status not in {"ok", "empty"}:
            status = "hybrid_api_only"
        elif api_result.metadata.status == "ok" and local_result.metadata.status == "ok":
            status = "hybrid_ok"

        return KnowledgeRetrievalResult(
            hits=merged_hits,
            metadata=KnowledgeRetrievalMetadata(
                backend_requested="hybrid",
                backend_used="hybrid",
                status=status,
                latency_ms=api_result.metadata.latency_ms + local_result.metadata.latency_ms,
                warning=" | ".join(warning_parts),
                result_count=len(merged_hits),
            ),
        )

    def _merge_hits(self, *groups: list[KnowledgeHit]) -> list[KnowledgeHit]:
        """Merge hits while preserving the highest-score variant of each knowledge item."""
        merged: dict[tuple[str, str], KnowledgeHit] = {}
        for group in groups:
            for item in group:
                key = (item.knowledge_id, item.title)
                previous = merged.get(key)
                if previous is None or item.score > previous.score:
                    merged[key] = item
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)

    def _maybe_api_fallback_or_soft_fail(
        self,
        *,
        query: str,
        limit: int,
        start: float,
        status: str,
        warning: str,
    ) -> KnowledgeRetrievalResult:
        if self._fallback_to_local and self._local_store is not None:
            local_result = self._search_local(query=query, limit=limit)
            metadata = local_result.metadata.model_copy(deep=True)
            metadata.backend_requested = self._backend
            metadata.backend_used = "local_fallback"
            metadata.status = "fallback_local" if local_result.hits else status
            metadata.warning = warning if not metadata.warning else f"{warning} | {metadata.warning}"
            metadata.latency_ms += int((perf_counter() - start) * 1000)
            metadata.result_count = len(local_result.hits)
            return KnowledgeRetrievalResult(hits=local_result.hits, metadata=metadata)
        return self._maybe_raise_or_soft_fail(status, warning, start)

    def _maybe_raise_or_soft_fail(
        self,
        status: str,
        warning: str,
        start: float,
    ) -> KnowledgeRetrievalResult:
        if not self._ignore_failure:
            raise KnowledgeBaseError(warning)
        return self._soft_failure(status, warning, start)

    def _soft_failure(self, status: str, warning: str, start: float) -> KnowledgeRetrievalResult:
        return KnowledgeRetrievalResult(
            metadata=KnowledgeRetrievalMetadata(
                backend_requested=self._backend,
                backend_used=self._backend,
                status=status,
                latency_ms=int((perf_counter() - start) * 1000),
                warning=warning,
                result_count=0,
            )
        )
