import { useEffect, useState, useCallback } from 'react';
import {
  CalendarClock,
  Plus,
  MoreHorizontal,
  Power,
  PowerOff,
  Trash2,
  Loader2,
} from 'lucide-react';
import client from '@/api/client';
import {
  listSchedules,
  createSchedule,
  deleteSchedule,
  toggleSchedule,
  type Schedule,
  type ScheduleCreate,
} from '@/api/schedules';

/* ─── Create modal ─── */
function CreateModal({
  onClose,
  onCreated,
  workflows,
}: {
  onClose: () => void;
  onCreated: () => void;
  workflows: { id: string; name: string }[];
}) {
  const [name, setName] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [cronExpr, setCronExpr] = useState('0 */6 * * *');
  const [timezone, setTimezone] = useState('UTC');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workflowId || !name || !cronExpr) return;
    setSaving(true);
    setError('');
    try {
      await createSchedule({
        workflow_id: workflowId,
        name,
        cron_expression: cronExpr,
        timezone,
      } as ScheduleCreate);
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create schedule');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-md space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">New Schedule</h2>
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. Daily report generation"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Workflow</label>
          <select
            required
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select workflow...</option>
            {workflows.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Cron Expression</label>
          <input
            type="text"
            required
            value={cronExpr}
            onChange={(e) => setCronExpr(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="0 */6 * * *"
          />
          <p className="text-xs text-slate-400 mt-1">Standard cron format: minute hour day month weekday</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Timezone</label>
          <select
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="UTC">UTC</option>
            <option value="Europe/Sofia">Europe/Sofia</option>
            <option value="Europe/London">Europe/London</option>
            <option value="America/New_York">America/New_York</option>
            <option value="America/Los_Angeles">America/Los_Angeles</option>
            <option value="Asia/Tokyo">Asia/Tokyo</option>
          </select>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition">
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-50 flex items-center gap-1.5"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Create
          </button>
        </div>
      </form>
    </div>
  );
}

/* ─── Main page ─── */
export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<{ id: string; name: string }[]>([]);
  const perPage = 25;

  const fetchSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSchedules({ page, per_page: perPage });
      setSchedules(data.items || []);
      setTotal(data.total || 0);
    } catch {
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  const fetchWorkflows = useCallback(async () => {
    try {
      const res = await client.get('/workflows/', { params: { per_page: 100 } });
      setWorkflows((res.data.workflows || []).map((w: { id: string; name: string }) => ({ id: w.id, name: w.name })));
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
    fetchWorkflows();
  }, [fetchSchedules, fetchWorkflows]);

  const handleToggle = async (id: string) => {
    try {
      await toggleSchedule(id);
      setActionMenu(null);
      fetchSchedules();
    } catch {
      // error
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this schedule?')) return;
    try {
      await deleteSchedule(id);
      setActionMenu(null);
      fetchSchedules();
    } catch {
      // error
    }
  };

  const totalPages = Math.ceil(total / perPage);

  function formatNextRun(iso?: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = d.getTime() - now.getTime();
    if (diffMs < 0) return 'overdue';
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `in ${diffMin}m`;
    if (diffMin < 1440) return `in ${Math.floor(diffMin / 60)}h`;
    return d.toLocaleDateString();
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Schedules</h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} schedule{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          New Schedule
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : schedules.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <CalendarClock className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">No schedules yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            Create your first schedule
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Workflow</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Cron</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Next Run</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {schedules.map((sched) => (
                <tr key={sched.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <p className="text-sm font-medium text-slate-900">{sched.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{sched.timezone}</p>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-600">{sched.workflow_name || sched.workflow_id.slice(0, 8)}</td>
                  <td className="px-5 py-3.5">
                    <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">{sched.cron_expression}</code>
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        sched.is_enabled
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-50 text-slate-500 border-slate-200'
                      }`}
                    >
                      {sched.is_enabled ? <><Power className="w-3 h-3" /> Enabled</> : <><PowerOff className="w-3 h-3" /> Disabled</>}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">{formatNextRun(sched.next_run_at)}</td>
                  <td className="px-3 py-3.5 relative">
                    <button
                      onClick={() => setActionMenu(actionMenu === sched.id ? null : sched.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </button>
                    {actionMenu === sched.id && (
                      <div className="absolute right-3 top-12 z-20 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                        <button
                          onClick={() => handleToggle(sched.id)}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                        >
                          {sched.is_enabled ? <><PowerOff className="w-3.5 h-3.5" /> Disable</> : <><Power className="w-3.5 h-3.5" /> Enable</>}
                        </button>
                        <hr className="my-1 border-slate-100" />
                        <button
                          onClick={() => handleDelete(sched.id)}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-500">Page {page} of {totalPages}</p>
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

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={fetchSchedules}
          workflows={workflows}
        />
      )}
    </div>
  );
}
