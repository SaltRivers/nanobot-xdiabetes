"""Shared helpers for X-Diabetes tool implementations."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def dump_json(data: Any) -> str:
    """Pretty-print JSON for tool responses."""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def load_model_json(raw: str, model_cls: type[T]) -> T:
    """Parse a JSON string into a Pydantic model instance."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Expected valid JSON payload: {exc}") from exc
    return model_cls.model_validate(payload)


def load_json_list(raw: str) -> list[dict[str, Any]]:
    """Parse a JSON list of objects with a helpful error message."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Expected valid JSON list payload: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list payload.")
    return payload
