import { useState } from "react";
import { useAppStore } from "../store";

export function GoalInput() {
  const [goal, setGoal] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { addTask, sidecarConnected, handleSidecarEvent } = useAppStore();

  const handleSubmit = async () => {
    const trimmed = goal.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);

    try {
      // Generate a temporary ID (sidecar will return the real one)
      const tempId = `task_${Date.now().toString(36)}`;
      addTask(tempId, trimmed);

      if (window.cowork) {
        const result = await window.cowork.startTask(trimmed, files);

        // If sidecar returned a completed/failed result directly,
        // update the task with the real result
        if (result.task_id) {
          if (result.status === "completed") {
            handleSidecarEvent({
              type: "task_completed",
              task_id: tempId,
              summary: result.summary || "Task completed.",
              tokens_used: result.tokens_used || 0,
              steps_completed: result.steps_completed || 0,
            });
          } else if (result.status === "failed") {
            handleSidecarEvent({
              type: "task_failed",
              task_id: tempId,
              error: result.error || "Unknown error",
            });
          }
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      // Show the error in the task
      const { tasks } = useAppStore.getState();
      const latest = tasks[0];
      if (latest) {
        handleSidecarEvent({
          type: "task_failed",
          task_id: latest.id,
          error: message,
        });
      }
    } finally {
      setGoal("");
      setFiles([]);
      setIsSubmitting(false);
    }
  };

  const handleAttachFiles = async () => {
    if (!window.cowork) return;
    const selected = await window.cowork.selectFiles();
    if (selected.length > 0) {
      setFiles((prev) => [...prev, ...selected]);
    }
  };

  const handleAttachFolder = async () => {
    if (!window.cowork) return;
    const folder = await window.cowork.selectFolder();
    if (folder) {
      setFiles((prev) => [...prev, folder]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="goal-input-container">
      <h2>What do you need done?</h2>
      <p>
        Describe your goal and Cowork will plan, execute, and deliver the result.
        Attach files or folders for context.
      </p>

      <div className="goal-form">
        <textarea
          className="goal-textarea"
          placeholder='e.g. "Organize my Downloads folder by file type" or "Summarize all the PDFs in ~/Documents/reports"'
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSubmitting}
          autoFocus
        />

        {files.length > 0 && (
          <div className="attached-files">
            {files.map((file, i) => (
              <div key={i} className="attached-file">
                <span>{file.split(/[/\\]/).pop()}</span>
                <span className="remove-file" onClick={() => removeFile(i)}>
                  ×
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="goal-actions">
          <div style={{ display: "flex", gap: "8px" }}>
            <button className="attach-btn" onClick={handleAttachFiles} disabled={isSubmitting}>
              📎 Files
            </button>
            <button className="attach-btn" onClick={handleAttachFolder} disabled={isSubmitting}>
              📁 Folder
            </button>
          </div>

          <button
            className="submit-btn"
            onClick={handleSubmit}
            disabled={!goal.trim() || isSubmitting || !sidecarConnected}
          >
            {isSubmitting ? "Working…" : "Start Task"}
            {!isSubmitting && " →"}
          </button>
        </div>

        {!sidecarConnected && (
          <div style={{ marginTop: "12px", fontSize: "12px", color: "var(--error)" }}>
            Agent not connected. Check Settings for configuration.
          </div>
        )}
      </div>
    </div>
  );
}
