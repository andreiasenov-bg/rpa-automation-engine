import client from './client';

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_email: string | null;
  resource_type: string;
  resource_id: string;
  action: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogList {
  audit_logs: AuditLogEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface AuditStats {
  total: number;
  by_action: Record<string, number>;
  by_resource_type: Record<string, number>;
}

export const auditApi = {
  list: async (
    page = 1,
    perPage = 50,
    filters: {
      resource_type?: string;
      action?: string;
      user_id?: string;
      search?: string;
      date_from?: string;
      date_to?: string;
    } = {},
  ): Promise<AuditLogList> => {
    const params: Record<string, string | number> = { page, per_page: perPage };
    if (filters.resource_type) params.resource_type = filters.resource_type;
    if (filters.action) params.action = filters.action;
    if (filters.user_id) params.user_id = filters.user_id;
    if (filters.search) params.search = filters.search;
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    const { data } = await client.get('/audit-logs', { params });
    return data;
  },

  stats: async (): Promise<AuditStats> => {
    const { data } = await client.get('/audit-logs/stats');
    return data;
  },

  resourceTypes: async (): Promise<string[]> => {
    const { data } = await client.get('/audit-logs/resource-types');
    return data.resource_types;
  },

  actions: async (): Promise<string[]> => {
    const { data } = await client.get('/audit-logs/actions');
    return data.actions;
  },
};
