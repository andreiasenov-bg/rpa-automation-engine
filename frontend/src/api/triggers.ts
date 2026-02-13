import client from './client';
import type { Trigger } from '@/types';

export interface TriggerCreateRequest {
  workflow_id: string;
  name: string;
  trigger_type: string;
  config: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface TriggerUpdateRequest {
  name?: string;
  config?: Record<string, unknown>;
}

export const triggerApi = {
  list: (page = 1, perPage = 20, filters?: { workflow_id?: string }) =>
    client.get<{ triggers: Trigger[]; total: number; page: number; per_page: number }>(
      '/triggers/', { params: { page, per_page: perPage, ...filters } }
    ).then((r) => r.data),

  get: (id: string) =>
    client.get<Trigger>(`/triggers/${id}`).then((r) => r.data),

  create: (data: TriggerCreateRequest) =>
    client.post<Trigger>('/triggers/', data).then((r) => r.data),

  update: (id: string, data: TriggerUpdateRequest) =>
    client.put<Trigger>(`/triggers/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    client.delete(`/triggers/${id}`),

  toggle: (id: string) =>
    client.post<Trigger>(`/triggers/${id}/toggle`).then((r) => r.data),

  fire: (id: string) =>
    client.post<{ message: string }>(`/triggers/${id}/fire`).then((r) => r.data),
};
