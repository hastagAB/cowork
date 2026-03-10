import { create } from "zustand";
import type { TaskState, StepInfo, SidecarEvent, TaskStatus, AppConfig } from "./types";

type View = "home" | "task" | "settings";

interface AppStore {
  // Navigation
  view: View;
  setView: (view: View) => void;

  // Connection
  sidecarConnected: boolean;
  setSidecarConnected: (connected: boolean) => void;

  // Tasks
  tasks: TaskState[];
  activeTaskId: string | null;
  setActiveTask: (id: string | null) => void;
  getActiveTask: () => TaskState | undefined;

  // Task lifecycle
  addTask: (id: string, goal: string) => void;
  updateTaskStatus: (id: string, status: TaskStatus) => void;
  addStep: (id: string, step: StepInfo) => void;
  updateStepStatus: (id: string, stepNumber: number, status: StepInfo["status"], error?: string) => void;
  completeTask: (id: string, summary: string, tokensUsed: number, stepsCompleted: number) => void;
  failTask: (id: string, error: string) => void;

  // Process sidecar events
  handleSidecarEvent: (event: SidecarEvent) => void;

  // Config
  config: AppConfig | null;
  setConfig: (config: AppConfig) => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  // Navigation
  view: "home",
  setView: (view) => set({ view }),

  // Connection
  sidecarConnected: false,
  setSidecarConnected: (connected) => set({ sidecarConnected: connected }),

  // Tasks
  tasks: [],
  activeTaskId: null,
  setActiveTask: (id) => set({ activeTaskId: id, view: id ? "task" : "home" }),
  getActiveTask: () => {
    const { tasks, activeTaskId } = get();
    return tasks.find((t) => t.id === activeTaskId);
  },

  // Task lifecycle
  addTask: (id, goal) =>
    set((state) => ({
      tasks: [
        { id, goal, status: "planning", steps: [], createdAt: new Date().toISOString() },
        ...state.tasks,
      ],
      activeTaskId: id,
      view: "task",
    })),

  updateTaskStatus: (id, status) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === id ? { ...t, status } : t)),
    })),

  addStep: (id, step) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, steps: [...t.steps, step] } : t
      ),
    })),

  updateStepStatus: (id, stepNumber, status, error) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id
          ? {
              ...t,
              steps: t.steps.map((s) =>
                s.stepNumber === stepNumber ? { ...s, status, error: error ?? s.error } : s
              ),
            }
          : t
      ),
    })),

  completeTask: (id, summary, tokensUsed, stepsCompleted) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id
          ? {
              ...t,
              status: "completed" as TaskStatus,
              result: { task_id: id, status: "completed", summary, tokens_used: tokensUsed, steps_completed: stepsCompleted },
            }
          : t
      ),
    })),

  failTask: (id, error) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id
          ? {
              ...t,
              status: "failed" as TaskStatus,
              result: { task_id: id, status: "failed", error },
            }
          : t
      ),
    })),

  // Process sidecar events
  handleSidecarEvent: (event) => {
    const store = get();
    switch (event.type) {
      case "task_started":
        // Task already added via addTask before sending request
        break;
      case "planning":
      case "thinking":
        store.updateTaskStatus(event.task_id, "planning");
        break;
      case "plan_created":
        store.updateTaskStatus(event.task_id, "running");
        break;
      case "step_started":
        store.updateTaskStatus(event.task_id, "running");
        store.addStep(event.task_id, {
          stepNumber: event.step_number,
          tool: event.tool,
          description: event.description,
          status: "running",
        });
        break;
      case "step_completed":
        store.updateStepStatus(event.task_id, event.step_number, "completed");
        break;
      case "step_failed":
        store.updateStepStatus(event.task_id, event.step_number, "failed", event.error);
        break;
      case "replanning":
        store.updateTaskStatus(event.task_id, "planning");
        break;
      case "verifying":
        store.updateTaskStatus(event.task_id, "running");
        break;
      case "task_completed":
        store.completeTask(event.task_id, event.summary, event.tokens_used, event.steps_completed);
        break;
      case "task_failed":
        store.failTask(event.task_id, event.error);
        break;
      case "sidecar_disconnected":
        set({ sidecarConnected: false });
        break;
    }
  },

  // Config
  config: null,
  setConfig: (config) => set({ config }),
}));
