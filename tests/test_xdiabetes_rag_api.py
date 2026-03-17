from pathlib import Path
from unittest.mock import patch

import httpx

from nanobot.x_diabetes import prepare_xdiabetes_workspace
from nanobot.x_diabetes.services import KnowledgeRouter, KnowledgeStore, RAGAPIClient


def test_knowledge_router_soft_fails_when_api_is_unavailable(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    router = KnowledgeRouter(
        backend="api",
        local_store=KnowledgeStore(tmp_path / "knowledge"),
        api_client=RAGAPIClient(base_url="http://127.0.0.1:8008"),
        ignore_failure=True,
        fallback_to_local=False,
        default_top_k=3,
    )

    with patch(
        "nanobot.x_diabetes.services.rag_api_client.httpx.post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        result = router.search(query="diabetic kidney disease follow-up", patient_id="demo_patient")

    assert result.hits == []
    assert result.metadata.status == "api_connection_error"
    assert result.metadata.result_count == 0
    assert "continuing without external evidence" in result.metadata.warning.lower()


def test_knowledge_router_can_fallback_to_local_results(tmp_path: Path):
    prepare_xdiabetes_workspace(tmp_path, mode="doctor", silent=True)

    router = KnowledgeRouter(
        backend="api",
        local_store=KnowledgeStore(tmp_path / "knowledge"),
        api_client=RAGAPIClient(base_url="http://127.0.0.1:8008"),
        ignore_failure=True,
        fallback_to_local=True,
        default_top_k=3,
    )

    with patch(
        "nanobot.x_diabetes.services.rag_api_client.httpx.post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        result = router.search(query="kidney complication diabetes", patient_id="demo_patient")

    assert result.hits
    assert result.metadata.backend_used == "local_fallback"
    assert result.metadata.result_count >= 1
