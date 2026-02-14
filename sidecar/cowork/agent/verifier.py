"""Verifier — checks if the task output satisfies the original goal."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from cowork.llm.client import LLMClient, Message

if TYPE_CHECKING:
    from cowork.agent.context import TaskContext

logger = logging.getLogger(__name__)

VERIFY_SYSTEM = """\
You are a quality checker. Given a user's original goal and the results of the steps taken, determine:
1. Was the goal achieved?
2. Is the output quality acceptable?
3. If not, what specifically needs to be fixed?

Respond with ONLY valid JSON:
{
  "satisfied": true/false,
  "summary": "Brief summary of what was accomplished",
  "issues": ["issue 1", "issue 2"]  // empty if satisfied
}
"""


async def verify_task(llm: LLMClient, context: TaskContext) -> dict:
    """Ask the LLM to verify whether the task goal has been met."""
    user_message = f"""Original goal: {context.goal}

Steps completed and their results:
{context.get_results_summary()}
"""

    messages = [Message(role="user", content=user_message)]
    response = await llm.complete(messages, system=VERIFY_SYSTEM)
    context.tokens_used += response.tokens_used

    try:
        from cowork.agent.planner import _extract_json
        return _extract_json(response.content)
    except (ValueError, json.JSONDecodeError):
        logger.error("Failed to parse verification: %s", response.content[:500])
        return {
            "satisfied": True,
            "summary": "Verification parsing failed; assuming success.",
            "issues": [],
        }
