import client from './client';

export interface Integration {
  id: string;
  name: string;
  integration_type: string;
  description: string;
  base_url: string;
  auth_type: string;
  status: string;
  enabled: boolean;
  tags?: string[];
  health_status?: string;
  last_health_check?: string;
  success_rate?: number;
  total_requests?: number;
  avg_response_ms?: number;
}

export interface IntegrationCreate {
  name: string;
  integration_type: string;
  base_url: string;
  description?: string;
  auth_type?: string;
  credential_id?: string;
  headers?: Record<string, string>;
  timeout_seconds?: number;
  health_check_url?: string;
  tags?: string[];
  enabled?: boolean;
}

export const integrationsApi = {
  list: () =>
    client.get<Integration[]>('/integrations/').then((r) => r.data),

  dashboard: () =>
    client.get('/integrations/dashboard').then((r) => r.data),

  get: (id: string) =>
    client.get<Integration>(`/integrations/${id}`).then((r) => r.data),

  create: (data: IntegrationCreate) =>
    client.post<Integration>('/integrations/', data).then((r) => r.data),

  update: (id: string, data: Partial<IntegrationCreate>) =>
    client.put<Integration>(`/integrations/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    client.delete(`/integrations/${id}`),

  toggle: (id: string) =>
    client.post(`/integrations/${id}/toggle`).then((r) => r.data),

  healthCheck: (id: string) =>
    client.post(`/integrations/${id}/health-check`).then((r) => r.data),

  healthCheckAll: () =>
    client.post('/integrations/health-check-all').then((r) => r.data),

  test: (id: string, method: string, path: string) =>
    client.post(`/integrations/${id}/test`, { method, path }).then((r) => r.data),

  healthHistory: (id: string) =>
    client.get(`/integrations/${id}/health-history`).then((r) => r.data),
};
