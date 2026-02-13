import client from './client';
import type { Workflow, WorkflowCreateRequest, Execution } from '@/types';

export const workflowApi = {
  list: (page = 1, perPage = 20) =>
    client.get<{ workflows: Workflow[]; total: number; page: number; per_page: number }>(
      '/workflows/', { params: { page, per_page: perPage } }
    ).then((r) => r.data),

  get: (id: string) =>
    client.get<Workflow>(`/workflows/${id}`).then((r) => r.data),

  create: (data: WorkflowCreateRequest) =>
    client.post<Workflow>('/workflows/', data).then((r) => r.data),

  update: (id: string, data: Partial<WorkflowCreateRequest> & { is_enabled?: boolean }) =>
    client.put<Workflow>(`/workflows/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    client.delete(`/workflows/${id}`),

  publish: (id: string) =>
    client.post<Workflow>(`/workflows/${id}/publish`).then((r) => r.data),

  archive: (id: string) =>
    client.post<Workflow>(`/workflows/${id}/archive`).then((r) => r.data),

  execute: (id: string, variables?: Record<string, unknown>) =>
    client.post<Execution>(`/workflows/${id}/execute`, variables ? { variables } : undefined).then((r) => r.data),
};
