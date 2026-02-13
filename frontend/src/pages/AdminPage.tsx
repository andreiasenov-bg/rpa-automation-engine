import { useEffect, useState, useCallback } from 'react';
import {
  Shield,
  Building2,
  Users,
  GitBranch,
  Server,
  Key,
  Play,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  X,
  Lock,
  UserPlus,
  UserMinus,
  ChevronDown,
  Check,
} from 'lucide-react';
import { adminApi, type OrgOverview, type RoleInfo, type PermissionInfo, type RoleUsersResponse } from '@/api/admin';
import { useLocale } from '@/i18n';

/* ─── Stat Card ─── */
function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-lg font-bold text-slate-900 dark:text-white">{value}</p>
      </div>
    </div>
  );
}

/* ─── Create Role Modal ─── */
function CreateRoleModal({ permissions, onClose, onDone }: { permissions: PermissionInfo[]; onClose: () => void; onDone: () => void }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  const handleSlugify = (val: string) => {
    setName(val);
    setSlug(val.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''));
  };

  const togglePerm = (id: string) => {
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCreate = async () => {
    if (!name.trim() || !slug.trim() || saving) return;
    setSaving(true);
    try {
      await adminApi.createRole(name.trim(), slug.trim());
      onDone();
    } catch {
      // handle
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Create Role</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Role Name</label>
            <input type="text" value={name} onChange={(e) => handleSlugify(e.target.value)} placeholder="e.g. Reviewer"
              className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Slug</label>
            <input type="text" value={slug} onChange={(e) => setSlug(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 font-mono" />
          </div>
          {permissions.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Permissions</label>
              <div className="max-h-40 overflow-y-auto border border-slate-200 dark:border-slate-600 rounded-lg divide-y divide-slate-100 dark:divide-slate-600">
                {permissions.map((p) => (
                  <label key={p.id} className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700">
                    <input type="checkbox" checked={selectedPerms.has(p.id)} onChange={() => togglePerm(p.id)}
                      className="w-3.5 h-3.5 rounded border-slate-300" />
                    <span className="text-xs text-slate-700 dark:text-slate-200">{p.code}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition">Cancel</button>
          <button onClick={handleCreate} disabled={!name.trim() || !slug.trim() || saving}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Assign Role Modal ─── */
function AssignRoleModal({
  roles,
  users,
  onClose,
  onDone,
}: {
  roles: RoleInfo[];
  users: Array<{ id: string; email: string; first_name: string; last_name: string; roles: string[] }>;
  onClose: () => void;
  onDone: () => void;
}) {
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [saving, setSaving] = useState(false);

  const handleAssign = async () => {
    if (!selectedUser || !selectedRole || saving) return;
    setSaving(true);
    try {
      await adminApi.assignRole(selectedUser, selectedRole);
      onDone();
    } catch {
      // handle
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-indigo-500" /> Assign Role
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">User</label>
            <select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white">
              <option value="">Select user...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.email} ({u.first_name} {u.last_name})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Role</label>
            <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white">
              <option value="">Select role...</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>{r.name} ({r.slug})</option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition">Cancel</button>
          <button onClick={handleAssign} disabled={!selectedUser || !selectedRole || saving}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Assign'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Role Users Panel ─── */
function RoleUsersPanel({ role, onRemove }: { role: RoleInfo; onRemove: (userId: string, roleId: string) => void }) {
  const [data, setData] = useState<RoleUsersResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const loadUsers = async () => {
    if (data) { setExpanded(!expanded); return; }
    setLoading(true);
    try {
      const res = await adminApi.usersByRole(role.id);
      setData(res);
      setExpanded(true);
    } catch {
      // handle
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={loadUsers} className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-600 mt-1">
        {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ChevronDown className={`w-3 h-3 transition ${expanded ? 'rotate-180' : ''}`} />}
        {expanded ? 'Hide users' : 'Show users'}
      </button>
      {expanded && data && (
        <div className="mt-2 space-y-1">
          {data.users.length === 0 && <p className="text-xs text-slate-400">No users assigned</p>}
          {data.users.map((u) => (
            <div key={u.id} className="flex items-center justify-between px-2 py-1.5 rounded bg-slate-50 dark:bg-slate-700/50">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-[10px] font-bold text-indigo-600">
                  {u.first_name[0]}{u.last_name[0]}
                </div>
                <span className="text-xs text-slate-700 dark:text-slate-200">{u.email}</span>
              </div>
              <button onClick={() => onRemove(u.id, role.id)} className="p-1 text-slate-400 hover:text-red-500">
                <UserMinus className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Permission Matrix ─── */
function PermissionMatrix({ roles, permissions }: { roles: RoleInfo[]; permissions: PermissionInfo[] }) {
  if (permissions.length === 0 || roles.length === 0) {
    return <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">No permissions or roles configured</p>;
  }

  // Group permissions by resource
  const groups = new Map<string, PermissionInfo[]>();
  permissions.forEach((p) => {
    const [resource] = p.code.split('.');
    if (!groups.has(resource)) groups.set(resource, []);
    groups.get(resource)!.push(p);
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-600">
            <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Permission</th>
            {roles.map((r) => (
              <th key={r.id} className="text-center py-2 px-2 text-slate-500 dark:text-slate-400 font-medium min-w-[80px]">
                {r.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from(groups.entries()).map(([resource, perms]) => (
            <>
              <tr key={resource}>
                <td colSpan={roles.length + 1} className="pt-3 pb-1 px-3 text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 tracking-wider">
                  {resource}
                </td>
              </tr>
              {perms.map((p) => (
                <tr key={p.id} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="py-1.5 px-3 text-slate-700 dark:text-slate-200 font-mono">{p.code}</td>
                  {roles.map((r) => {
                    const has = r.permissions.some((rp) => rp.id === p.id);
                    return (
                      <td key={r.id} className="text-center py-1.5 px-2">
                        {has ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500 mx-auto" />
                        ) : (
                          <span className="w-3.5 h-3.5 block mx-auto text-slate-300 dark:text-slate-600">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Main Page ─── */
export default function AdminPage() {
  const { t } = useLocale();
  const [overview, setOverview] = useState<OrgOverview | null>(null);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [permissions, setPermissions] = useState<PermissionInfo[]>([]);
  const [users, setUsers] = useState<Array<{ id: string; email: string; first_name: string; last_name: string; roles: string[] }>>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [showAssignRole, setShowAssignRole] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'roles' | 'permissions' | 'users'>('overview');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, rl, pm] = await Promise.all([
        adminApi.overview(),
        adminApi.roles(),
        adminApi.permissions(),
      ]);
      setOverview(ov);
      setRoles(rl.roles || []);
      setPermissions(pm.permissions || []);

      // Also fetch users list
      try {
        const { data } = await (await import('@/api/client')).default.get('/users/');
        setUsers(data.users || []);
      } catch {
        // users endpoint might not be available
      }
    } catch {
      // handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDeleteRole = async (id: string, slug: string) => {
    if (slug === 'admin') return;
    if (!confirm('Delete this role?')) return;
    await adminApi.deleteRole(id);
    fetchData();
  };

  const handleRemoveRole = async (userId: string, roleId: string) => {
    if (!confirm('Remove this role from user?')) return;
    try {
      await adminApi.removeRole(userId, roleId);
      fetchData();
    } catch {
      // handle
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const tabs = [
    { key: 'overview' as const, label: t('admin.overview') },
    { key: 'roles' as const, label: t('admin.roles') },
    { key: 'permissions' as const, label: t('admin.permissions') },
    { key: 'users' as const, label: t('nav.users') },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            {t('admin.title')}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {overview?.organization?.name} &mdash; {overview?.organization?.plan} plan
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 dark:bg-slate-700/50 rounded-lg p-1 w-fit">
        {tabs.map(({ key, label }) => (
          <button key={key} onClick={() => setActiveTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition ${
              activeTab === key ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && overview && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <StatCard label="Users" value={overview?.counts?.users ?? 0} icon={Users} color="bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400" />
            <StatCard label="Workflows" value={overview?.counts?.workflows ?? 0} icon={GitBranch} color="bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400" />
            <StatCard label="Agents" value={overview?.counts?.agents ?? 0} icon={Server} color="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400" />
            <StatCard label="Credentials" value={overview?.counts?.credentials ?? 0} icon={Key} color="bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Total Executions" value={overview?.counts?.executions_total ?? 0} icon={Play} color="bg-slate-50 text-slate-600 dark:bg-slate-700 dark:text-slate-300" />
            <StatCard label="Running" value={overview?.counts?.executions_running ?? 0} icon={Loader2} color="bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400" />
            <StatCard label="Failed" value={overview?.counts?.executions_failed ?? 0} icon={AlertCircle} color="bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400" />
          </div>

          <div className="mt-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
              <Building2 className="w-4 h-4" /> Organization Details
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-slate-400">Name</p>
                <p className="font-medium text-slate-900 dark:text-white">{overview?.organization?.name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Plan</p>
                <p className="font-medium text-slate-900 dark:text-white capitalize">{overview?.organization?.plan}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Organization ID</p>
                <p className="font-mono text-xs text-slate-600 dark:text-slate-300">{overview?.organization?.id}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Created</p>
                <p className="text-slate-600 dark:text-slate-300">{overview?.organization?.created_at ? new Date(overview?.organization?.created_at).toLocaleDateString() : '—'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Roles Tab */}
      {activeTab === 'roles' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">{roles.length} role{roles.length !== 1 ? 's' : ''}</p>
            <button onClick={() => setShowCreateRole(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">
              <Plus className="w-4 h-4" /> {t('admin.createRole')}
            </button>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700">
            {roles.map((role) => (
              <div key={role.id} className="px-5 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
                      {role.slug === 'admin' && <Lock className="w-3 h-3 text-amber-500" />}
                      {role.name}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">{role.slug}</p>
                    {role.permissions.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {role.permissions.slice(0, 5).map((p) => (
                          <span key={p.id} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300">{p.code}</span>
                        ))}
                        {role.permissions.length > 5 && (
                          <span className="text-[10px] text-slate-400">+{role.permissions.length - 5} more</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {role.slug !== 'admin' && (
                      <button onClick={() => handleDeleteRole(role.id, role.slug)}
                        className="p-1.5 text-slate-400 hover:text-red-500 transition">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
                <RoleUsersPanel role={role} onRemove={handleRemoveRole} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Permissions Tab — Matrix View */}
      {activeTab === 'permissions' && (
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{permissions.length} permission{permissions.length !== 1 ? 's' : ''} &times; {roles.length} roles</p>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <PermissionMatrix roles={roles} permissions={permissions} />
          </div>
        </div>
      )}

      {/* Users Tab — Role assignments */}
      {activeTab === 'users' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">{users.length} user{users.length !== 1 ? 's' : ''}</p>
            <button onClick={() => setShowAssignRole(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">
              <UserPlus className="w-4 h-4" /> Assign Role
            </button>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700">
            {users.map((user) => (
              <div key={user.id} className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    {user.first_name?.[0] || ''}{user.last_name?.[0] || ''}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{user.first_name} {user.last_name}</p>
                    <p className="text-xs text-slate-400">{user.email}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {(user.roles || []).map((roleName) => (
                    <span key={roleName} className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium">
                      {roleName}
                    </span>
                  ))}
                  {(!user.roles || user.roles.length === 0) && (
                    <span className="text-[10px] text-slate-400 italic">No roles</span>
                  )}
                </div>
              </div>
            ))}
            {users.length === 0 && (
              <div className="px-5 py-8 text-center">
                <p className="text-sm text-slate-400">No users found</p>
              </div>
            )}
          </div>
        </div>
      )}

      {showCreateRole && (
        <CreateRoleModal
          permissions={permissions}
          onClose={() => setShowCreateRole(false)}
          onDone={() => { setShowCreateRole(false); fetchData(); }}
        />
      )}

      {showAssignRole && (
        <AssignRoleModal
          roles={roles}
          users={users}
          onClose={() => setShowAssignRole(false)}
          onDone={() => { setShowAssignRole(false); fetchData(); }}
        />
      )}
    </div>
  );
}
