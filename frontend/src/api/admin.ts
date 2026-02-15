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

export interface UserRolesResponse {
  user_id: string;
  email: string;
  roles: Array<{ id: string; name: string; slug: string; description: string }>;
}

export interface RoleUsersResponse {
  role: { id: string; name: string; slug: string };
  users: Array<{ id: string; email: string; first_name: string; last_name: string; is_active: boolean }>;
}

export interface BulkAssignResult {
  success: number;
  skipped: number;
  errors: Array<{ user_id: string; error: string }>;
  role: { id: string; name: string };
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

  // ─── User-Role Assignment ──────────────────────────────
  getUserRoles: async (userId: string): Promise<UserRolesResponse> => {
    const { data } = await client.get(`/user-roles/${userId}/roles`);
    return data;
  },

  assignRole: async (userId: string, roleId: string): Promise<void> => {
    await client.post(`/user-roles/${userId}/roles`, { role_id: roleId });
  },

  removeRole: async (userId: string, roleId: string): Promise<void> => {
    await client.delete(`/user-roles/${userId}/roles/${roleId}`);
  },

  usersByRole: async (roleId: string): Promise<RoleUsersResponse> => {
    const { data } = await client.get(`/user-roles/by-role/${roleId}`);
    return data;
  },

  bulkAssignRole: async (userIds: string[], roleId: string): Promise<BulkAssignResult> => {
    const { data } = await client.post('/user-roles/bulk-assign', { user_ids: userIds, role_id: roleId });
    return data;
  },

  // ─── Role Permission Assignment ────────────────────────
  updateRolePermissions: async (roleId: string, permissionIds: string[]): Promise<void> => {
    await client.put(`/admin/roles/${roleId}`, { permission_ids: permissionIds });
  },

  // ─── System Configuration ─────────────────────────────
  getConfig: async (): Promise<{ config: Record<string, string> }> => {
    const { data } = await client.get('/admin/config');
    return data;
  },

  setConfig: async (key: string, value: string): Promise<void> => {
    await client.put('/admin/config', { key, value });
  },

  deleteConfig: async (key: string): Promise<void> => {
    await client.delete(`/admin/config/${key}`);
  },
};
