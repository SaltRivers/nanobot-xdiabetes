"""Tool registry for dynamic tool management."""

import json
from typing import Any

from loguru import logger

from xdiabetes.agent.tools.base import Tool


def _truncate_params(params: dict[str, Any], max_len: int = 500) -> str:
    """Serialize params to JSON, truncating if too long."""
    try:
        s = json.dumps(params, ensure_ascii=False, default=str)
    except Exception:
        s = str(params)
    if len(s) > max_len:
        return s[:max_len] + "...(truncated)"
    return s


class ToolRegistry:
    """
    Registry for agent tools.

    Allows dynamic registration and execution of tools.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """Execute a tool by name with given parameters."""
        _HINT = "\n\n[Analyze the error above and try a different approach.]"

        tool = self._tools.get(name)
        if not tool:
            logger.warning("Tool not found: '{}'. Available: {}", name, ", ".join(self.tool_names))
            return f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"

        try:
            # Attempt to cast parameters to match schema types
            params = tool.cast_params(params)

            # Validate parameters
            errors = tool.validate_params(params)
            if errors:
                logger.debug("Tool '{}' param validation failed: {}", name, errors)
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors) + _HINT
            logger.debug("Executing tool '{}' with params: {}", name, _truncate_params(params))
            result = await tool.execute(**params)
            if isinstance(result, str) and result.startswith("Error"):
                logger.debug("Tool '{}' returned error result: {}", name, result[:300])
                return result + _HINT
            logger.debug(
                "Tool '{}' succeeded, result length: {}",
                name,
                len(result) if isinstance(result, str) else "N/A",
            )
            return result
        except Exception as e:
            logger.debug("Tool '{}' raised exception: {}", name, str(e)[:300])
            return f"Error executing {name}: {str(e)}" + _HINT

    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
