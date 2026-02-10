"""Executor — runs individual steps by dispatching to tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cowork.models import PlanStep, Step, StepStatus, ToolResult

if TYPE_CHECKING:
    from cowork.agent.context import TaskContext
    from cowork.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


async def execute_step(
    plan_step: PlanStep,
    context: TaskContext,
    registry: ToolRegistry,
) -> ToolResult:
    """Execute a single plan step by finding and calling the appropriate tool."""
    tool = registry.get(plan_step.tool)
    if tool is None:
        return ToolResult(
            success=False,
            error=f"Unknown tool: {plan_step.tool}. Available: {[t.name for t in registry.list_all()]}",
        )

    try:
        args = plan_step.args or {}
        result = await tool.execute(args, context)
    except KeyError as exc:
        logger.error("Tool %s missing required argument: %s. Received: %s", plan_step.tool, exc, list((plan_step.args or {}).keys()))
        result = ToolResult(
            success=False,
            error=f"Missing required argument {exc} for tool '{plan_step.tool}'. Received args: {list((plan_step.args or {}).keys())}",
        )
    except Exception as exc:
        logger.exception("Tool %s raised an exception", plan_step.tool)
        result = ToolResult(success=False, error=f"Tool execution error: {exc}")

    return result
