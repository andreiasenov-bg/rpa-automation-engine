/**
 * Dashboard API module — stats and overview data.
 */

import client from './client';

export interface DashboardStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  running_executions: number;
  completed_executions: number;
  failed_executions: number;
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await client.get<DashboardStats>('/dashboard/stats');
  return data;
}
