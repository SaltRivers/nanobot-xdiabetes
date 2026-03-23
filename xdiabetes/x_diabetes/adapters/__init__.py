"""DTMH adapter exports and factory helpers."""

from __future__ import annotations

from xdiabetes.config.schema import XDiabetesConfig
from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.adapters.http import HTTPDTMHAdapter
from xdiabetes.x_diabetes.adapters.mcp import MCPDTMHAdapter
from xdiabetes.x_diabetes.adapters.mock import MockDTMHAdapter
from xdiabetes.x_diabetes.adapters.python_bridge import PythonDTMHAdapter
from xdiabetes.x_diabetes.errors import DTMHAdapterError


def build_dtmh_adapter(config: XDiabetesConfig) -> DTMHAdapter:
    """Build the configured DTMH adapter.

    The mock backend is intentionally the default because the real DTMH is still
    training for this repository state.
    """

    backend = config.dtmh.backend
    if backend == "mock":
        return MockDTMHAdapter()
    if backend == "python":
        return PythonDTMHAdapter(config.dtmh.python_entrypoint)
    if backend == "http":
        return HTTPDTMHAdapter(config.dtmh.http_base_url, timeout_s=config.dtmh.timeout_s)
    if backend == "mcp":
        return MCPDTMHAdapter(config.dtmh.mcp_server_name)
    if backend == "disabled":
        raise DTMHAdapterError(
            "DTMH backend is disabled. Switch xDiabetes.dtmh.backend to 'mock', 'python', or 'http'."
        )
    raise DTMHAdapterError(f"Unsupported DTMH backend: {backend}")


__all__ = [
    "DTMHAdapter",
    "MockDTMHAdapter",
    "PythonDTMHAdapter",
    "HTTPDTMHAdapter",
    "MCPDTMHAdapter",
    "build_dtmh_adapter",
]
