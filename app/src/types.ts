// Electron preload API exposed via contextBridge
export interface CoworkAPI {
  startTask: (goal: string, files?: string[]) => Promise<TaskResult>;
  getConfig: () => Promise<AppConfig>;
  setConfig: (key: string, value: string) => Promise<{ ok: boolean }>;
  listTools: () => Promise<{ tools: ToolSchema[] }>;
  pingSidecar: () => Promise<{ ok: boolean; pong?: boolean; error?: string }>;
  selectFolder: () => Promise<string | null>;
  selectFiles: () => Promise<string[]>;
  onSidecarEvent: (callback: (event: SidecarEvent) => void) => () => void;
}

declare global {
  interface Window {
    cowork: CoworkAPI;
  }
}

// Task-related types
export type TaskStatus =
  | "planning"
  | "running"
  | "confirming"
  | "completed"
  | "failed"
  | "cancelled";

export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface TaskResult {
  task_id: string;
  status: string;
  summary?: string;
  tokens_used?: number;
  steps_completed?: number;
  error?: string;
}

export interface StepInfo {
  stepNumber: number;
  tool: string;
  description: string;
  status: StepStatus;
  error?: string;
}

export interface TaskState {
  id: string;
  goal: string;
  status: TaskStatus;
  steps: StepInfo[];
  result?: TaskResult;
  createdAt: string;
}

// Sidecar events
export type SidecarEvent =
  | { type: "task_started"; task_id: string; goal: string }
  | { type: "planning"; task_id: string }
  | { type: "thinking"; task_id: string; iteration: number }
  | { type: "plan_created"; task_id: string; reasoning: string; step_count: number }
  | { type: "step_started"; task_id: string; step_number: number; tool: string; description: string }
  | { type: "step_completed"; task_id: string; step_number: number; tool: string }
  | { type: "step_failed"; task_id: string; step_number: number; tool: string; error: string }
  | { type: "replanning"; task_id: string; attempt?: number; reason?: string }
  | { type: "verifying"; task_id: string }
  | { type: "task_completed"; task_id: string; summary: string; tokens_used: number; steps_completed: number }
  | { type: "task_failed"; task_id: string; error: string };

// Config types
export interface AppConfig {
  llm: {
    provider: string;
    model: string;
    has_api_key: boolean;
    base_url: string;
    endpoint: string;
    deployment: string;
    api_version: string;
    max_tokens: number;
    temperature: number;
  };
  permissions: {
    allowed_paths: string[];
    confirm_destructive: boolean;
    dry_run: boolean;
  };
  agent: {
    max_steps_per_task: number;
    max_replans: number;
    task_timeout_seconds: number;
  };
}

export interface ToolSchema {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}
