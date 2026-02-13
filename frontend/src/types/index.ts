/* ─── Auth ──────────────────────────────── */
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  org_id: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  org_name: string;
}

/* ─── Workflow ──────────────────────────── */
export interface Workflow {
  id: string;
  name: string;
  description: string;
  definition: WorkflowDefinition;
  version: number;
  is_enabled: boolean;
  status: 'draft' | 'published' | 'archived';
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDefinition {
  steps: WorkflowStep[];
  entry_point?: string;
  variables?: Record<string, unknown>;
}

export interface WorkflowStep {
  id: string;
  type: string;
  name?: string;
  config: Record<string, unknown>;
  next?: string[];
  on_error?: string;
  position?: { x: number; y: number };
}

export interface WorkflowCreateRequest {
  name: string;
  description?: string;
  definition: Record<string, unknown>;
}

/* ─── Execution ────────────────────────── */
export interface Execution {
  id: string;
  workflow_id: string;
  agent_id?: string;
  trigger_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  retry_count: number;
}

export interface ExecutionLog {
  id: string;
  level: string;
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
}

/* ─── Trigger ──────────────────────────── */
export interface Trigger {
  id: string;
  workflow_id: string;
  name: string;
  trigger_type: string;
  config: Record<string, unknown>;
  is_enabled: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  error_message?: string;
}

/* ─── Pagination ───────────────────────── */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}
