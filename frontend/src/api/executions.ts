import client from './client';
import type { Execution, ExecutionLog } from '@/types';

export const executionApi = {
  list: (page = 1, perPage = 20, filters?: { workflow_id?: string; status?: string }) =>
    client.get<{ executions: Execution[]; total: number; page: number; per_page: number }>(
      '/executions/', { params: { page, per_page: perPage, ...filters } }
    ).then((r) => r.data),

  get: (id: string) =>
    client.get<Execution>(`/executions/${id}`).then((r) => r.data),

  logs: (id: string) =>
    client.get<ExecutionLog[]>(`/executions/${id}/logs`).then((r) => r.data),

  retry: (id: string) =>
    client.post<Execution>(`/executions/${id}/retry`).then((r) => r.data),

  cancel: (id: string) =>
    client.post<{ message: string }>(`/executions/${id}/cancel`).then((r) => r.data),
};
