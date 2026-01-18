"""Base tool interface and tool registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from cowork.models import ToolResult

if TYPE_CHECKING:
    from cowork.agent.context import TaskContext


class BaseTool(ABC):
    """Base class for all agent-callable tools."""

    name: str
    description: str
    parameters: dict  # JSON Schema
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(self, args: dict, context: TaskContext) -> ToolResult:
        """Execute the tool with the given arguments."""
        ...

    def to_llm_schema(self) -> dict:
        """Convert to a schema the LLM can use for tool selection."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI function-calling tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_llm_schemas(self) -> list[dict]:
        return [tool.to_llm_schema() for tool in self._tools.values()]

    def to_openai_tools(self) -> list[dict]:
        """Get all tools in OpenAI function-calling format."""
        return [tool.to_openai_tool() for tool in self._tools.values()]


def create_default_registry() -> ToolRegistry:
    """Create a registry with all Phase 1 tools registered."""
    from cowork.tools.fs import (
        ListDirectoryTool,
        ReadFileTool,
        WriteFileTool,
        GetFileInfoTool,
        SearchFilesGlobTool,
        CreateDirectoryTool,
    )

    registry = ToolRegistry()
    registry.register(ListDirectoryTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(GetFileInfoTool())
    registry.register(SearchFilesGlobTool())
    registry.register(CreateDirectoryTool())
    return registry
