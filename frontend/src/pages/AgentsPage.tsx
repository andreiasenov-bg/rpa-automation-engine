import { useEffect, useState, useCallback } from 'react';
import {
  Search,
  Plus,
  Loader2,
  Server,
  Copy,
  Trash2,
  RefreshCw,
  Wifi,
  WifiOff,
  X,
  Eye,
  EyeOff,
  RotateCw,
} from 'lucide-react';
import { agentsApi, type AgentInfo, type AgentStats } from '@/api/agents';

/* ─── Status badge ─── */
const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  active: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  inactive: { bg: 'bg-slate-50', text: 'text-slate-600', dot: 'bg-slate-400' },
  disconnected: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  error: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
};

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS.inactive;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${status === 'active' ? 'animate-pulse' : ''}`} />
      {status}
    </span>
  );
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const diff = Date.now() - new Date(iso).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/* ─── Register Modal ─── */
function RegisterModal({ onClose, onDone }: { onClose: () => void; onDone: (token: string) => void }) {
  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [saving, setSaving] = useState(false);

  const handleRegister = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      const res = await agentsApi.register(name.trim(), version);
      onDone(res.token);
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
          <h2 className="text-lg font-semibold text-slate-900">Register New Agent</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Agent Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. worker-01"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Version</label>
            <input type="text" value={version} onChange={(e) => setVersion(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition">Cancel</button>
          <button onClick={handleRegister} disabled={!name.trim() || saving}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Register'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Token Display ─── */
function TokenModal({ token, onClose }: { token: string; onClose: () => void }) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-2">Agent Token</h2>
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
          Save this token now — it will not be shown again!
        </p>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-xs bg-slate-900 text-emerald-400 px-3 py-2 rounded-lg overflow-x-auto">
            {visible ? token : '•'.repeat(48)}
          </code>
          <button onClick={() => setVisible(!visible)} className="text-slate-400 hover:text-slate-600">
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
          <button onClick={copy} className="text-slate-400 hover:text-slate-600">
            <Copy className="w-4 h-4" />
          </button>
        </div>
        {copied && <p className="text-xs text-emerald-600 mt-1">Copied!</p>}
        <div className="flex justify-end mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">Done</button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─── */
export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [tokenToShow, setTokenToShow] = useState('');
  const perPage = 20;

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const filters: { status?: string; search?: string } = {};
      if (search) filters.search = search;
      if (statusFilter) filters.status = statusFilter;
      const data = await agentsApi.list(page, perPage, filters);
      setAgents(data.agents || []);
      setTotal(data.total || 0);
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);
  useEffect(() => { agentsApi.stats().then(setStats).catch(() => {}); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Remove this agent?')) return;
    await agentsApi.remove(id);
    fetchAgents();
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Server className="w-6 h-6 text-indigo-500" />
            Agents
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {stats ? `${stats.online} online / ${stats.total} total` : `${total} agents`}
          </p>
        </div>
        <button onClick={() => setShowRegister(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition">
          <Plus className="w-4 h-4" /> Register Agent
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Total</p>
            <p className="text-xl font-bold text-slate-900">{stats.total}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Online</p>
            <p className="text-xl font-bold text-emerald-600">{stats.online}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Inactive</p>
            <p className="text-xl font-bold text-slate-500">{stats.by_status.inactive || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Errors</p>
            <p className="text-xl font-bold text-red-600">{stats.by_status.error || 0}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input type="text" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search agents..." className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300" />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="disconnected">Disconnected</option>
          <option value="error">Error</option>
        </select>
        <button onClick={fetchAgents} className="p-2 text-slate-400 hover:text-slate-600 border border-slate-200 rounded-lg">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      {loading && agents.length === 0 ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : agents.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <Server className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No agents registered</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="px-5 py-2 flex items-center gap-4 border-b border-slate-100 text-[10px] font-medium uppercase text-slate-400">
            <span className="w-44">Name</span>
            <span className="w-24">Status</span>
            <span className="w-20">Version</span>
            <span className="flex-1">Last Heartbeat</span>
            <span className="w-32">Created</span>
            <span className="w-20">Actions</span>
          </div>
          {agents.map((agent) => (
            <div key={agent.id} className="px-5 py-3 flex items-center gap-4 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
              <div className="w-44">
                <p className="text-sm font-medium text-slate-900 truncate">{agent.name}</p>
                <p className="text-[10px] text-slate-400 font-mono">{agent.id.slice(0, 8)}...</p>
              </div>
              <div className="w-24"><StatusBadge status={agent.status} /></div>
              <div className="w-20 text-xs text-slate-600">{agent.version}</div>
              <div className="flex-1 flex items-center gap-1 text-xs text-slate-500">
                {agent.status === 'active' ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-slate-300" />}
                {relativeTime(agent.last_heartbeat_at)}
              </div>
              <div className="w-32 text-xs text-slate-400">{agent.created_at ? new Date(agent.created_at).toLocaleDateString() : '—'}</div>
              <div className="w-20 flex gap-1">
                <button onClick={() => handleDelete(agent.id)} className="p-1 text-slate-400 hover:text-red-500 transition" title="Remove">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}

          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition">Previous</button>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition">Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onDone={(token) => { setShowRegister(false); setTokenToShow(token); fetchAgents(); }}
        />
      )}
      {tokenToShow && (
        <TokenModal token={tokenToShow} onClose={() => setTokenToShow('')} />
      )}
    </div>
  );
}
