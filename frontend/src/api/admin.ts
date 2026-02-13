import client from './client';

export interface OrgOverview {
  organization: {
    id: string;
    name: string;
    plan: string;
    created_at: string | null;
  };
  counts: {
    users: number;
    workflows: number;
    agents: number;
    credentials: number;
    executions_total: number;
    executions_running: number;
    executions_failed: number;
  };
}

export interface RoleInfo {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  permissions: Array<{ id: string; code: string; name: string }>;
  created_at: string | null;
}

export interface PermissionInfo {
  id: string;
  code: string;
  name: string;
  description: string | null;
}

export const adminApi = {
  overview: async (): Promise<OrgOverview> => {
    const { data } = await client.get('/admin/overview');
    return data;
  },

  updateOrg: async (body: { name?: string; plan?: string }): Promise<void> => {
    await client.put('/admin/organization', body);
  },

  roles: async (): Promise<{ roles: RoleInfo[]; total: number }> => {
    const { data } = await client.get('/admin/roles');
    return data;
  },

  createRole: async (name: string, slug: string): Promise<void> => {
    await client.post('/admin/roles', { name, slug });
  },

  updateRole: async (id: string, body: { name?: string; description?: string }): Promise<void> => {
    await client.put(`/admin/roles/${id}`, body);
  },

  deleteRole: async (id: string): Promise<void> => {
    await client.delete(`/admin/roles/${id}`);
  },

  permissions: async (): Promise<{ permissions: PermissionInfo[] }> => {
    const { data } = await client.get('/admin/permissions');
    return data;
  },
};
