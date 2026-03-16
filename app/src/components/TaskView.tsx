import { useAppStore } from "../store";
import type { StepInfo } from "../types";

export function TaskView() {
  const task = useAppStore((s) => {
    const id = s.activeTaskId;
    return id ? s.tasks.find((t) => t.id === id) : undefined;
  });

  if (!task) {
    return (
      <div className="goal-input-container">
        <p>Select a task from the sidebar or start a new one.</p>
      </div>
    );
  }

  return (
    <div className="task-view">
      <div className="task-header">
        <h2>{task.goal}</h2>
        <div className="task-status">
          <span className={`status-dot ${task.status}`} />
          <span>{formatStatus(task.status)}</span>
          {task.result?.steps_completed && (
            <>
              <span>·</span>
              <span>{task.result.steps_completed} steps</span>
            </>
          )}
          {task.result?.tokens_used && (
            <>
              <span>·</span>
              <span>{task.result.tokens_used.toLocaleString()} tokens</span>
            </>
          )}
        </div>
      </div>

      <div className="task-body">
        {/* Activity Feed */}
        <div className="activity-feed">
          {task.status === "planning" && task.steps.length === 0 && (
            <div className="step-card">
              <div className="step-icon running">⚡</div>
              <div className="step-content">
                <div className="step-title">Planning...</div>
                <div className="step-detail">Breaking down your goal into steps</div>
              </div>
            </div>
          )}

          {task.steps.map((step) => (
            <StepCard key={step.stepNumber} step={step} />
          ))}
        </div>

        {/* Result */}
        {task.result && task.status === "completed" && (
          <div className="result-panel">
            <h3>✅ Result</h3>
            <div className="result-summary">{task.result.summary}</div>
            <div className="result-meta">
              <span>{task.result.steps_completed} steps completed</span>
              <span>{task.result.tokens_used?.toLocaleString()} tokens used</span>
            </div>
          </div>
        )}

        {/* Error */}
        {task.result && task.status === "failed" && (
          <div className="result-panel" style={{ borderColor: "var(--error)" }}>
            <h3 style={{ color: "var(--error)" }}>❌ Failed</h3>
            <div className="result-summary" style={{ color: "var(--error)" }}>
              {task.result.error}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StepCard({ step }: { step: StepInfo }) {
  const iconMap: Record<string, string> = {
    running: "⏳",
    completed: "✓",
    failed: "✗",
    pending: "○",
    skipped: "–",
  };

  return (
    <div className="step-card">
      <div className={`step-icon ${step.status}`}>{iconMap[step.status] || "○"}</div>
      <div className="step-content">
        <div className="step-title">
          {step.description}
        </div>
        <div className="step-detail">{step.tool}</div>
        {step.error && <div className="step-error">{step.error}</div>}
      </div>
    </div>
  );
}

function formatStatus(status: string): string {
  const map: Record<string, string> = {
    planning: "Planning...",
    running: "Working...",
    confirming: "Waiting for confirmation...",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}
