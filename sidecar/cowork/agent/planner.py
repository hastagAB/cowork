"""Planner — uses the LLM to break a goal into executable steps."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from cowork.llm.client import LLMClient, Message
from cowork.models import Plan, PlanStep

if TYPE_CHECKING:
    from cowork.agent.context import TaskContext
    from cowork.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output, handling markdown fences and surrounding text."""
    raw = text.strip()
    if not raw:
        raise ValueError("LLM returned empty response")

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find first { ... last } as JSON object
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    logger.error("Could not extract JSON from LLM response: %s", raw[:500])
    raise ValueError(f"Could not extract JSON from LLM response (length={len(raw)})")

SYSTEM_PROMPT = """\
You are a task planner for Cowork, a local desktop AI agent. Your job is to break down a user's goal into a concrete step-by-step plan.

RULES:
1. Each step must use EXACTLY ONE tool from the available tools list.
2. Steps execute sequentially — later steps can use results from earlier steps.
3. Be specific with file paths and arguments. Use the EXACT parameter names shown.
4. If the goal is ambiguous, start with exploration steps (list_directory, read_file) before action steps.
5. Prefer creating NEW files over overwriting existing ones.
6. Always end with a summary/deliverable step if the goal implies producing output.
7. Keep plans focused — 3 to 8 steps is ideal.

CRITICAL: Respond with ONLY a valid JSON object. No markdown fences. No explanation text. Just the raw JSON.

Output format:
{
  "reasoning": "Brief explanation of your approach",
  "steps": [
    {"step_number": 1, "tool": "tool_name", "args": {"param": "value"}, "reason": "Why this step"}
  ]
}
"""

MAX_LLM_RETRIES = 2


async def create_plan(
    llm: LLMClient,
    context: TaskContext,
    registry: ToolRegistry,
) -> Plan:
    """Ask the LLM to create a step-by-step plan for the task."""
    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description} | Parameters: {list(t.parameters.get('properties', {}).keys())} (required: {t.parameters.get('required', [])})"
        for t in registry.list_all()
    )

    user_message = f"""Goal: {context.goal}

Available tools:
{tool_descriptions}

Attached files: {json.dumps(context.attached_files) if context.attached_files else "None"}
"""

    if context.step_results:
        user_message += f"\n\nPrevious step results (re-planning):\n{context.get_results_summary()}"

    messages = [Message(role="user", content=user_message)]

    last_error = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        response = await llm.complete(messages, system=SYSTEM_PROMPT)
        context.tokens_used += response.tokens_used

        try:
            data = _extract_json(response.content)
            steps = [PlanStep(**s) for s in data.get("steps", [])]
            return Plan(steps=steps, reasoning=data.get("reasoning", ""))
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Plan parse attempt %d failed: %s", attempt + 1, exc)

    logger.error("Failed to parse plan from LLM after %d attempts: %s", MAX_LLM_RETRIES + 1, response.content[:500])
    raise ValueError(f"LLM returned invalid plan JSON after {MAX_LLM_RETRIES + 1} attempts: {last_error}") from last_error


async def create_replan(
    llm: LLMClient,
    context: TaskContext,
    registry: ToolRegistry,
    failure_reason: str,
) -> Plan:
    """Re-plan after a failure, incorporating what we learned."""
    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description} | Parameters: {list(t.parameters.get('properties', {}).keys())} (required: {t.parameters.get('required', [])})"
        for t in registry.list_all()
    )

    user_message = f"""Goal: {context.goal}

Available tools:
{tool_descriptions}

PREVIOUS ATTEMPT RESULTS:
{context.get_results_summary()}

FAILURE REASON: {failure_reason}

Create a new plan that avoids the previous failure. Build on what already succeeded.
Only include REMAINING steps — do not repeat steps that already completed successfully.
"""

    messages = [Message(role="user", content=user_message)]

    last_error = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        response = await llm.complete(messages, system=SYSTEM_PROMPT)
        context.tokens_used += response.tokens_used

        try:
            data = _extract_json(response.content)
            steps = [PlanStep(**s) for s in data.get("steps", [])]
            return Plan(steps=steps, reasoning=data.get("reasoning", ""))
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Replan parse attempt %d failed: %s", attempt + 1, exc)

    logger.error("Failed to parse replan from LLM after %d attempts: %s", MAX_LLM_RETRIES + 1, response.content[:500])
    raise ValueError(f"LLM returned invalid replan JSON after {MAX_LLM_RETRIES + 1} attempts: {last_error}") from last_error
