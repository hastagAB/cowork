"""Task context — holds state for a running task."""

from __future__ import annotations

from dataclasses import dataclass, field

from cowork.models import Step, ToolResult


@dataclass
class TaskContext:
    """Mutable context carried through each step of a task."""

    task_id: str
    goal: str
    attached_files: list[str] = field(default_factory=list)
    working_dir: str | None = None

    # Accumulates results from each executed step
    step_results: list[tuple[Step, ToolResult]] = field(default_factory=list)

    # Token counter
    tokens_used: int = 0

    # Conversation history for the agent
    conversation: list[dict] = field(default_factory=list)

    def add_result(self, step: Step, result: ToolResult) -> None:
        self.step_results.append((step, result))

    def get_results_summary(self) -> str:
        """Summarize all step results for the LLM context."""
        lines = []
        for step, result in self.step_results:
            status = "OK" if result.success else "FAILED"
            data_preview = ""
            if result.data:
                data_preview = str(result.data)[:500]
            elif result.error:
                data_preview = result.error
            lines.append(
                f"Step {step.step_number} [{step.tool_name}] → {status}: {data_preview}"
            )
        return "\n".join(lines)
