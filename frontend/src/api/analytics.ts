/**
 * Analytics API module — execution stats and performance metrics.
 */

import client from './client';

export interface ExecutionOverview {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_duration_ms: number;
  success_rate: number;
  period_days: number;
}

export interface TimelineEntry {
  timestamp: string | null;
  count: number;
}

export interface ExecutionTimeline {
  interval: string;
  period_days: number;
  timeline: TimelineEntry[];
}

export interface WorkflowPerformanceEntry {
  workflow_id: string;
  workflow_name: string;
  execution_count: number;
  success_count: number;
  failure_count: number;
  average_duration_ms: number;
  success_rate: number;
  last_execution: string | null;
}

export interface WorkflowPerformance {
  period_days: number;
  limit: number;
  workflows: WorkflowPerformanceEntry[];
}

export async function fetchExecutionOverview(days = 7): Promise<ExecutionOverview> {
  const { data } = await client.get<ExecutionOverview>('/analytics/overview', {
    params: { days },
  });
  return data;
}

export async function fetchExecutionTimeline(
  days = 7,
  interval: 'hour' | 'day' | 'week' = 'day',
): Promise<ExecutionTimeline> {
  const { data } = await client.get<ExecutionTimeline>('/analytics/executions/timeline', {
    params: { days, interval },
  });
  return data;
}

export async function fetchWorkflowPerformance(
  days = 7,
  limit = 10,
): Promise<WorkflowPerformance> {
  const { data } = await client.get<WorkflowPerformance>('/analytics/workflows/performance', {
    params: { days, limit },
  });
  return data;
}
