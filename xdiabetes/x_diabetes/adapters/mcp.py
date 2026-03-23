"""Placeholder MCP adapter for future DTMH integration.

The current MVP keeps DTMH local to the native tool layer. When the real model is
ready, the recommended path is either:
1. expose it via HTTP and use the HTTP adapter; or
2. expose it as an MCP tool and let the runtime call that MCP tool directly.
"""

from __future__ import annotations

from xdiabetes.x_diabetes.adapters.base import DTMHAdapter
from xdiabetes.x_diabetes.errors import DTMHAdapterError
from xdiabetes.x_diabetes.schemas import DTMHRequest, DTMHResult


class MCPDTMHAdapter(DTMHAdapter):
    """Explicit placeholder that documents the intended future integration path."""

    def __init__(self, server_name: str):
        self._server_name = server_name.strip()

    @property
    def backend_name(self) -> str:
        return "mcp"

    def analyze(self, request: DTMHRequest) -> DTMHResult:  # pragma: no cover - explicit placeholder
        raise DTMHAdapterError(
            "The MCP DTMH adapter is reserved for future integration. "
            f"Expose the real DTMH via HTTP or register MCP tools from server '{self._server_name or 'unset'}'."
        )
