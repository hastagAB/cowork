import { useAppStore } from "../store";

export function Sidebar() {
  const { tasks, activeTaskId, setActiveTask, setView, sidecarConnected } = useAppStore();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">C</div>
        <h1>Cowork</h1>
      </div>

      <button
        className="new-task-btn"
        onClick={() => {
          setActiveTask(null);
          setView("home");
        }}
      >
        + New Task
      </button>

      <div className="task-list">
        {tasks.map((task) => (
          <div
            key={task.id}
            className={`task-item ${task.id === activeTaskId ? "active" : ""}`}
            onClick={() => setActiveTask(task.id)}
          >
            <div className="task-item-goal">{task.goal}</div>
            <div className="task-item-meta">
              <span className={`status-dot ${task.status}`} />
              <span>{formatStatus(task.status)}</span>
              <span>·</span>
              <span>{formatTime(task.createdAt)}</span>
            </div>
          </div>
        ))}

        {tasks.length === 0 && (
          <div style={{ padding: "20px", color: "var(--text-muted)", textAlign: "center", fontSize: "13px" }}>
            No tasks yet. Start by describing what you need done.
          </div>
        )}
      </div>

      <div
        className="sidebar-footer"
        onClick={() => setView("settings")}
        style={{ cursor: "pointer" }}
      >
        <span className={`connection-dot ${sidecarConnected ? "connected" : "disconnected"}`} />
        <span>{sidecarConnected ? "Agent connected" : "Agent disconnected"}</span>
      </div>
    </aside>
  );
}

function formatStatus(status: string): string {
  const map: Record<string, string> = {
    planning: "Planning",
    running: "Working",
    confirming: "Waiting",
    completed: "Done",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return map[status] || status;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}
