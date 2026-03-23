"""Local knowledge retrieval for the X-Diabetes MVP."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from xdiabetes.x_diabetes.constants import DEFAULT_KNOWLEDGE_LIMIT
from xdiabetes.x_diabetes.errors import KnowledgeBaseError
from xdiabetes.x_diabetes.schemas import KnowledgeHit

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-\u4e00-\u9fff]+")


class KnowledgeStore:
    """Simple lexical retrieval over local seed documents and manifest metadata."""

    def __init__(self, knowledge_dir: Path):
        self._knowledge_dir = knowledge_dir
        self._knowledge_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._knowledge_dir / "manifest.json"

    def search(self, query: str, limit: int = DEFAULT_KNOWLEDGE_LIMIT) -> list[KnowledgeHit]:
        """Search the local knowledge base.

        The implementation is intentionally lightweight: it scores by token overlap
        across titles, tags, summaries, and document text. That keeps the MVP free
        from extra vector database dependencies while still giving the agent a
        deterministic evidence source.
        """

        query = query.strip()
        if not query:
            return []

        entries = self._load_manifest()
        tokens = set(self._tokenize(query))
        hits: list[KnowledgeHit] = []
        for entry in entries:
            content = self._load_document(entry.get("file", ""))
            haystack = " ".join(
                [
                    str(entry.get("title", "")),
                    " ".join(entry.get("tags", [])),
                    str(entry.get("summary", "")),
                    content,
                ]
            ).lower()
            score = sum(3 if token in str(entry.get("title", "")).lower() else 1 for token in tokens if token in haystack)
            if score <= 0:
                continue
            snippet = self._extract_snippet(content, tokens)
            hits.append(
                KnowledgeHit(
                    knowledge_id=str(entry.get("id", entry.get("title", "unknown"))),
                    title=str(entry.get("title", "Untitled")),
                    source=str(entry.get("source", "local")),
                    summary=str(entry.get("summary", "")),
                    tags=list(entry.get("tags", [])),
                    score=float(score),
                    file_path=str((self._knowledge_dir / str(entry.get("file", ""))).resolve()) if entry.get("file") else "",
                    snippet=snippet,
                )
            )

        return sorted(hits, key=lambda item: item.score, reverse=True)[: max(1, limit)]

    def _load_manifest(self) -> list[dict[str, Any]]:
        if not self._manifest_path.exists():
            raise KnowledgeBaseError(
                f"Knowledge manifest not found: {self._manifest_path}. Run xdiabetes onboard first."
            )
        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise KnowledgeBaseError(f"Knowledge manifest is not valid JSON: {self._manifest_path}") from exc

        if not isinstance(payload, list):
            raise KnowledgeBaseError("Knowledge manifest must be a JSON list.")
        return payload

    def _load_document(self, relative_path: str) -> str:
        if not relative_path:
            return ""
        path = self._knowledge_dir / relative_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_snippet(self, content: str, tokens: set[str]) -> str:
        if not content:
            return ""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        lowered_tokens = {token.lower() for token in tokens}
        for line in lines:
            lowered = line.lower()
            if any(token in lowered for token in lowered_tokens):
                return line[:280]
        return lines[0][:280] if lines else ""

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in _TOKEN_RE.findall(text)]
