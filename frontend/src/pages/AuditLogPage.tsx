import { useEffect, useState, useCallback } from 'react';
import {
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Loader2,
  ScrollText,
  Shield,
  User as UserIcon,
  Clock,
  ArrowUpDown,
} from 'lucide-react';
import { auditApi, type AuditLogEntry, type AuditStats } from '@/api/audit';

/* ─── Action color map ─── */
const ACTION_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  create: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  read: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  update: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  delete: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  execute: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200' },
  login: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  logout: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  export: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  decrypt: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
};

function ActionBadge({ action }: { action: string }) {
  const c = ACTION_COLORS[action] || { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${c.bg} ${c.text} ${c.border}`}>
      {action}
    </span>
  );
}

function ResourceBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
      {type}
    </span>
  );
}

function formatTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/* ─── Diff viewer ─── */
function DiffViewer({ oldVals, newVals }: { oldVals: Record<string, unknown> | null; newVals: Record<string, unknown> | null }) {
  if (!oldVals && !newVals) return <p className="text-xs text-slate-400 italic">No changes recorded</p>;

  const allKeys = new Set([...Object.keys(oldVals || {}), ...Object.keys(newVals || {})]);

  return (
    <div className="bg-slate-900 rounded-lg p-3 font-mono text-xs space-y-0.5 max-h-48 overflow-y-auto">
      {[...allKeys].map((key) => {
        const oldV = oldVals?.[key];
        const newV = newVals?.[key];
        const changed = JSON.stringify(oldV) !== JSON.stringify(newV);
        return (
          <div key={key} className="flex gap-2">
            <span className="text-slate-500 w-32 flex-shrink-0 truncate">{key}:</span>
            {changed ? (
              <>
                {oldV !== undefined && (
                  <span className="text-red-400 line-through">{JSON.stringify(oldV)}</span>
                )}
                {newV !== undefined && (
                  <span className="text-emerald-400">{JSON.stringify(newV)}</span>
                )}
              </>
            ) : (
              <span className="text-slate-400">{JSON.stringify(newV)}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Row ─── */
function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="px-5 py-3 flex items-center gap-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-slate-400 flex-shrink-0">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <div className="w-24 flex-shrink-0">
          <ActionBadge action={entry.action} />
        </div>

        <div className="w-24 flex-shrink-0">
          <ResourceBadge type={entry.resource_type} />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-600 truncate">
            {entry.resource_id.slice(0, 8)}...
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-500 flex-shrink-0 w-40">
          <UserIcon className="w-3 h-3" />
          <span className="truncate">{entry.user_email || 'system'}</span>
        </div>

        <div className="flex items-center gap-1 text-xs text-slate-400 flex-shrink-0 w-20" title={formatTime(entry.created_at)}>
          <Clock className="w-3 h-3" />
          {relativeTime(entry.created_at)}
        </div>

        {entry.ip_address && (
          <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded flex-shrink-0">
            {entry.ip_address}
          </span>
        )}
      </div>

      {expanded && (
        <div className="px-5 pb-4 pl-14">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <p className="text-[10px] font-medium text-slate-400 uppercase mb-1">Resource ID</p>
              <p className="text-xs text-slate-600 font-mono break-all">{entry.resource_id}</p>
            </div>
            <div>
              <p className="text-[10px] font-medium text-slate-400 uppercase mb-1">Timestamp</p>
              <p className="text-xs text-slate-600">{formatTime(entry.created_at)}</p>
            </div>
          </div>
          <p className="text-[10px] font-medium text-slate-400 uppercase mb-1">Changes</p>
          <DiffViewer oldVals={entry.old_values} newVals={entry.new_values} />
        </div>
      )}
    </div>
  );
}

/* ─── Main page ─── */
export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const perPage = 50;

  // Filters
  const [search, setSearch] = useState('');
  const [filterAction, setFilterAction] = useState('');
  const [filterResource, setFilterResource] = useState('');
  const [availableActions, setAvailableActions] = useState<string[]>([]);
  const [availableResources, setAvailableResources] = useState<string[]>([]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const filters: Record<string, string> = {};
      if (search) filters.search = search;
      if (filterAction) filters.action = filterAction;
      if (filterResource) filters.resource_type = filterResource;

      const data = await auditApi.list(page, perPage, filters);
      setEntries(data.audit_logs || []);
      setTotal(data.total || 0);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterAction, filterResource]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Load filter options & stats once
  useEffect(() => {
    auditApi.actions().then(setAvailableActions).catch(() => {});
    auditApi.resourceTypes().then(setAvailableResources).catch(() => {});
    auditApi.stats().then(setStats).catch(() => {});
  }, []);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            Audit Log
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} event{total !== 1 ? 's' : ''} recorded
          </p>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Total Events</p>
            <p className="text-xl font-bold text-slate-900">{stats.total}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Creates</p>
            <p className="text-xl font-bold text-emerald-600">{stats.by_action.create || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Updates</p>
            <p className="text-xl font-bold text-amber-600">{stats.by_action.update || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <p className="text-xs text-slate-500">Deletes</p>
            <p className="text-xl font-bold text-red-600">{stats.by_action.delete || 0}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search audit logs..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
          />
        </div>

        <select
          value={filterAction}
          onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="">All Actions</option>
          {availableActions.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>

        <select
          value={filterResource}
          onChange={(e) => { setFilterResource(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="">All Resources</option>
          {availableResources.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {loading && entries.length === 0 ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : entries.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <ScrollText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No audit log entries found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200">
          {/* Column headers */}
          <div className="px-5 py-2 flex items-center gap-4 border-b border-slate-100 text-[10px] font-medium uppercase text-slate-400">
            <span className="w-4" />
            <span className="w-24">Action</span>
            <span className="w-24">Resource</span>
            <span className="flex-1">ID</span>
            <span className="w-40">User</span>
            <span className="w-20">When</span>
          </div>

          {entries.map((entry) => (
            <AuditRow key={entry.id} entry={entry} />
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
