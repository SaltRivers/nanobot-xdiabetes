"""Local guideline retrieval tool for X-Diabetes."""

from __future__ import annotations

from typing import Any

from xdiabetes.agent.tools.base import Tool
from xdiabetes.x_diabetes.services import KnowledgeRouter

from .common import dump_json


class XDiabetesGuidelineSearchTool(Tool):
    """Search the local seed knowledge base."""

    def __init__(self, *, knowledge_router: KnowledgeRouter):
        self._knowledge_router = knowledge_router

    @property
    def name(self) -> str:
        return "xdiabetes_guideline_search"

    @property
    def description(self) -> str:
        return (
            "Search the local X-Diabetes guideline and knowledge base. Use this after patient analysis "
            "to gather supporting evidence, caveats, and follow-up guidance."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for diabetes guidance or evidence."},
                "patient_id": {
                    "type": "string",
                    "description": "Optional patient identifier used by the external RAG API for context-aware retrieval.",
                },
                "task": {
                    "type": "string",
                    "description": "Optional workflow type sent to the configured retrieval backend.",
                    "enum": ["general", "screening", "subtyping", "complication", "management", "followup"],
                },
                "audience": {
                    "type": "string",
                    "description": "Optional audience hint sent to the configured retrieval backend.",
                    "enum": ["doctor", "patient"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "minimum": 1,
                    "maximum": 10,
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Return retrieval metadata together with the hits.",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        query: str,
        patient_id: str = "",
        task: str = "general",
        audience: str = "doctor",
        limit: int = 3,
        include_metadata: bool = False,
        **_: Any,
    ) -> str:
        result = self._knowledge_router.search(
            query=query,
            patient_id=patient_id,
            task=task,
            audience=audience,
            limit=limit,
        )
        if include_metadata:
            return dump_json(result.model_dump(mode="json"))
        return dump_json([item.model_dump(mode="json") for item in result.hits])
