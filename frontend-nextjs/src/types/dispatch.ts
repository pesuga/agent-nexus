export type TaskStatus =
  | "backlog"
  | "todo"
  | "planning"
  | "hitl_review"
  | "working"
  | "ready_to_implement"
  | "approval"
  | "completed"
  | "blocked";

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  assignee: string | null;
  priority: number;
  created_at: string;
  updated_at: string;
  parent_id: string | null;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  status: "online" | "working" | "offline";
  last_heartbeat?: string;
  capabilities?: string[];
}

export interface User {
  id: string;
  email: string;
  display_name?: string;
  global_role: string;
  disabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthSession {
  actor_id: string;
  actor_role: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  global_role?: string;
}

export interface ModelRecord {
  id: string;
  label: string;
  provider: string;
  model_name: string;
  api_base?: string | null;
  is_default: boolean;
  enabled: boolean;
  config?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface AgentProfile {
  id: string;
  project_id: string;
  name: string;
  type: string;
  system_prompt?: string | null;
  model_id?: string | null;
  provider?: string | null;
  tools: string[];
  skills: string[];
  context_policy?: Record<string, unknown>;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AgentInstance {
  id: string;
  project_id: string;
  profile_id?: string | null;
  container_name?: string | null;
  status: string;
  task_id?: string | null;
  started_at?: string | null;
  last_heartbeat?: string | null;
  updated_at?: string | null;
}

export interface AgentActivityEvent {
  id: string;
  project_id: string;
  instance_id?: string | null;
  agent_id?: string | null;
  task_id?: string | null;
  level: string;
  message: string;
  ts: string;
}

export interface UIConfig {
  apiBaseUrl: string;
  actorRole: string;
  actorId: string;
  apiToken: string;
}
