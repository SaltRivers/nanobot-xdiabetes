"""Python bridge for future local DTMH integration."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.errors import DTMHAdapterError
from xdiabetes.x_diabetes.schemas import DTMHRequest, DTMHResult


class PythonDTMHAdapter(DTMHAdapter):
    """Call a local Python entrypoint of the form ``module.path:function_name``."""

    def __init__(self, entrypoint: str):
        self._entrypoint = entrypoint.strip()
        if not self._entrypoint or ":" not in self._entrypoint:
            raise DTMHAdapterError(
                "pythonEntrypoint must use 'module.path:function_name' format for the python backend."
            )
        self._callable = self._load_callable(self._entrypoint)

    @property
    def backend_name(self) -> str:
        return "python"

    def _load_callable(self, entrypoint: str) -> Callable[[dict[str, Any]], dict[str, Any] | DTMHResult]:
        module_name, func_name = entrypoint.split(":", 1)
        try:
            module = import_module(module_name)
        except Exception as exc:  # pragma: no cover - depends on user environment
            raise DTMHAdapterError(f"Failed to import DTMH module '{module_name}': {exc}") from exc

        callback = getattr(module, func_name, None)
        if callback is None or not callable(callback):
            raise DTMHAdapterError(
                f"Entrypoint '{entrypoint}' does not resolve to a callable DTMH function."
            )
        return callback

    def analyze(self, request: DTMHRequest) -> DTMHResult:
        try:
            raw = self._callable(request.model_dump(mode="python"))
        except Exception as exc:  # pragma: no cover - depends on user environment
            raise DTMHAdapterError(f"Python DTMH entrypoint failed: {exc}") from exc

        if isinstance(raw, DTMHResult):
            return raw
        if isinstance(raw, dict):
            return DTMHResult.model_validate(raw)
        raise DTMHAdapterError(
            "Python DTMH entrypoint returned an unsupported object. Expected dict or DTMHResult."
        )
