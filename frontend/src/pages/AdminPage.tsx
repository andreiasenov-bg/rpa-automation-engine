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
} from 'lucide-react';
import { adminApi, type OrgOverview, type RoleInfo, type PermissionInfo } from '@/api/admin';

/* ─── Stat Card ─── */
function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-lg font-bold text-slate-900">{value}</p>
      </div>
    </div>
  );
}

/* ─── Create Role Modal ─── */
function CreateRoleModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSlugify = (val: string) => {
    setName(val);
    setSlug(val.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''));
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
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Create Role</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Role Name</label>
            <input type="text" value={name} onChange={(e) => handleSlugify(e.target.value)} placeholder="e.g. Reviewer"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Slug</label>
            <input type="text" value={slug} onChange={(e) => setSlug(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 font-mono" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition">Cancel</button>
          <button onClick={handleCreate} disabled={!name.trim() || !slug.trim() || saving}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Page ─── */
export default function AdminPage() {
  const [overview, setOverview] = useState<OrgOverview | null>(null);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [permissions, setPermissions] = useState<PermissionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'roles' | 'permissions'>('overview');

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            Admin Panel
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {overview?.organization.name} &mdash; {overview?.organization.plan} plan
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
        {(['overview', 'roles', 'permissions'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition ${
              activeTab === tab ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && overview && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <StatCard label="Users" value={overview.counts.users} icon={Users} color="bg-blue-50 text-blue-600" />
            <StatCard label="Workflows" value={overview.counts.workflows} icon={GitBranch} color="bg-violet-50 text-violet-600" />
            <StatCard label="Agents" value={overview.counts.agents} icon={Server} color="bg-emerald-50 text-emerald-600" />
            <StatCard label="Credentials" value={overview.counts.credentials} icon={Key} color="bg-amber-50 text-amber-600" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Total Executions" value={overview.counts.executions_total} icon={Play} color="bg-slate-50 text-slate-600" />
            <StatCard label="Running" value={overview.counts.executions_running} icon={Loader2} color="bg-indigo-50 text-indigo-600" />
            <StatCard label="Failed" value={overview.counts.executions_failed} icon={AlertCircle} color="bg-red-50 text-red-600" />
          </div>

          <div className="mt-6 bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <Building2 className="w-4 h-4" /> Organization Details
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-slate-400">Name</p>
                <p className="font-medium text-slate-900">{overview.organization.name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Plan</p>
                <p className="font-medium text-slate-900 capitalize">{overview.organization.plan}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Organization ID</p>
                <p className="font-mono text-xs text-slate-600">{overview.organization.id}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Created</p>
                <p className="text-slate-600">{overview.organization.created_at ? new Date(overview.organization.created_at).toLocaleDateString() : '—'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Roles Tab */}
      {activeTab === 'roles' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-500">{roles.length} role{roles.length !== 1 ? 's' : ''}</p>
            <button onClick={() => setShowCreateRole(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">
              <Plus className="w-4 h-4" /> New Role
            </button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
            {roles.map((role) => (
              <div key={role.id} className="px-5 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900 flex items-center gap-2">
                    {role.slug === 'admin' && <Lock className="w-3 h-3 text-amber-500" />}
                    {role.name}
                  </p>
                  <p className="text-xs text-slate-400 font-mono">{role.slug}</p>
                  {role.permissions.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {role.permissions.slice(0, 5).map((p) => (
                        <span key={p.id} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{p.code}</span>
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
            ))}
          </div>
        </div>
      )}

      {/* Permissions Tab */}
      {activeTab === 'permissions' && (
        <div>
          <p className="text-sm text-slate-500 mb-4">{permissions.length} permission{permissions.length !== 1 ? 's' : ''}</p>
          <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
            {permissions.map((perm) => (
              <div key={perm.id} className="px-5 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">{perm.name}</p>
                  <p className="text-xs text-slate-400 font-mono">{perm.code}</p>
                </div>
              </div>
            ))}
            {permissions.length === 0 && (
              <div className="px-5 py-8 text-center">
                <p className="text-sm text-slate-400">No permissions configured yet</p>
              </div>
            )}
          </div>
        </div>
      )}

      {showCreateRole && (
        <CreateRoleModal
          onClose={() => setShowCreateRole(false)}
          onDone={() => { setShowCreateRole(false); fetchData(); }}
        />
      )}
    </div>
  );
}
