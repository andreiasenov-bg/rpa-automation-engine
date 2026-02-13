import client from './client';

export interface AgentInfo {
  id: string;
  name: string;
  status: string;
  version: string;
  capabilities: Record<string, unknown> | null;
  last_heartbeat_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentListResponse {
  agents: AgentInfo[];
  total: number;
  page: number;
  per_page: number;
  online_count: number;
}

export interface AgentStats {
  total: number;
  online: number;
  by_status: Record<string, number>;
}

export const agentsApi = {
  list: async (page = 1, perPage = 20, filters: { status?: string; search?: string } = {}): Promise<AgentListResponse> => {
    const params: Record<string, string | number> = { page, per_page: perPage };
    if (filters.status) params.status = filters.status;
    if (filters.search) params.search = filters.search;
    const { data } = await client.get('/agents', { params });
    return data;
  },

  stats: async (): Promise<AgentStats> => {
    const { data } = await client.get('/agents/stats');
    return data;
  },

  get: async (id: string): Promise<AgentInfo> => {
    const { data } = await client.get(`/agents/${id}`);
    return data;
  },

  register: async (name: string, version?: string, capabilities?: Record<string, unknown>): Promise<{ agent: AgentInfo; token: string }> => {
    const { data } = await client.post('/agents', { name, version: version || '1.0.0', capabilities });
    return data;
  },

  update: async (id: string, body: { name?: string; version?: string; capabilities?: Record<string, unknown> }): Promise<AgentInfo> => {
    const { data } = await client.put(`/agents/${id}`, body);
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await client.delete(`/agents/${id}`);
  },

  rotateToken: async (id: string): Promise<{ token: string }> => {
    const { data } = await client.post(`/agents/${id}/rotate-token`);
    return data;
  },
};
