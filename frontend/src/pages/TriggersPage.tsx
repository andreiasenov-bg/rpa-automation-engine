import { useEffect, useState, useCallback } from 'react';
import {
  Zap,
  Plus,
  MoreHorizontal,
  Power,
  PowerOff,
  Trash2,
  PlayCircle,
  Loader2,
  Clock,
  Globe,
  FileText,
  Mail,
  Database,
  Webhook,
  Eye,
} from 'lucide-react';
import type { Trigger } from '@/types';
import client from '@/api/client';
import { triggerApi, type TriggerCreateRequest } from '@/api/triggers';

/* ─── Trigger type config ─── */
const TRIGGER_TYPES: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  cron: { label: 'Cron Schedule', icon: Clock, color: '#6366f1' },
  webhook: { label: 'Webhook', icon: Webhook, color: '#0ea5e9' },
  file_watcher: { label: 'File Watcher', icon: Eye, color: '#10b981' },
  email: { label: 'Email', icon: Mail, color: '#f59e0b' },
  database: { label: 'Database', icon: Database, color: '#8b5cf6' },
  api_poll: { label: 'API Poll', icon: Globe, color: '#ec4899' },
  manual: { label: 'Manual', icon: PlayCircle, color: '#64748b' },
  event: { label: 'Event', icon: FileText, color: '#f97316' },
};

function TriggerTypeBadge({ type }: { type: string }) {
  const cfg = TRIGGER_TYPES[type] || { label: type, icon: Zap, color: '#64748b' };
  const Icon = cfg.icon;

  return (
    <div className="flex items-center gap-2">
      <div
        className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: `${cfg.color}15`, color: cfg.color }}
      >
        <Icon className="w-3.5 h-3.5" />
      </div>
      <span className="text-xs font-medium text-slate-600">{cfg.label}</span>
    </div>
  );
}

/* ─── Create trigger modal ─── */
function CreateTriggerModal({
  onClose,
  onCreated,
  workflowOptions,
}: {
  onClose: () => void;
  onCreated: () => void;
  workflowOptions: { id: string; name: string }[];
}) {
  const [name, setName] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [triggerType, setTriggerType] = useState('cron');
  const [cronExpr, setCronExpr] = useState('*/5 * * * *');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workflowId || !name) return;
    setSaving(true);

    const config: Record<string, unknown> = {};
    if (triggerType === 'cron') config.cron_expression = cronExpr;
    if (triggerType === 'webhook') config.method = 'POST';

    try {
      await triggerApi.create({
        workflow_id: workflowId,
        name,
        trigger_type: triggerType,
        config,
        is_enabled: true,
      });
      onCreated();
      onClose();
    } catch {
      // error
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-md space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">New Trigger</h2>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. Every 5 minutes"
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
            {workflowOptions.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
          <select
            value={triggerType}
            onChange={(e) => setTriggerType(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {Object.entries(TRIGGER_TYPES).map(([key, cfg]) => (
              <option key={key} value={key}>{cfg.label}</option>
            ))}
          </select>
        </div>

        {triggerType === 'cron' && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cron Expression</label>
            <input
              type="text"
              value={cronExpr}
              onChange={(e) => setCronExpr(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="*/5 * * * *"
            />
            <p className="text-xs text-slate-400 mt-1">Standard cron format (min hour day month weekday)</p>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition"
          >
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
export default function TriggersPage() {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [workflows, setWorkflows] = useState<{ id: string; name: string }[]>([]);
  const perPage = 25;

  const fetchTriggers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await triggerApi.list(page, perPage);
      setTriggers(data.triggers || []);
      setTotal(data.total || 0);
    } catch {
      setTriggers([]);
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
    fetchTriggers();
    fetchWorkflows();
  }, [fetchTriggers, fetchWorkflows]);

  const handleToggle = async (id: string) => {
    try {
      await triggerApi.toggle(id);
      setActionMenu(null);
      fetchTriggers();
    } catch {
      // error
    }
  };

  const handleFire = async (id: string) => {
    try {
      await triggerApi.fire(id);
      setActionMenu(null);
    } catch {
      // error
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this trigger?')) return;
    try {
      await triggerApi.delete(id);
      setActionMenu(null);
      fetchTriggers();
    } catch {
      // error
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Triggers</h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} trigger{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          New Trigger
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : triggers.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <Zap className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">No triggers yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            Create your first trigger
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Fires</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Last Fired</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {triggers.map((trigger) => (
                <tr key={trigger.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <p className="text-sm font-medium text-slate-900">{trigger.name}</p>
                    {trigger.error_message && (
                      <p className="text-xs text-red-500 mt-0.5 truncate max-w-xs">{trigger.error_message}</p>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <TriggerTypeBadge type={trigger.trigger_type} />
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        trigger.is_enabled
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-50 text-slate-500 border-slate-200'
                      }`}
                    >
                      {trigger.is_enabled ? (
                        <>
                          <Power className="w-3 h-3" /> Enabled
                        </>
                      ) : (
                        <>
                          <PowerOff className="w-3 h-3" /> Disabled
                        </>
                      )}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">{trigger.trigger_count}</td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {trigger.last_triggered_at
                      ? new Date(trigger.last_triggered_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="px-3 py-3.5 relative">
                    <button
                      onClick={() => setActionMenu(actionMenu === trigger.id ? null : trigger.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </button>

                    {actionMenu === trigger.id && (
                      <div className="absolute right-3 top-12 z-20 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                        <button
                          onClick={() => handleToggle(trigger.id)}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                        >
                          {trigger.is_enabled ? (
                            <>
                              <PowerOff className="w-3.5 h-3.5" /> Disable
                            </>
                          ) : (
                            <>
                              <Power className="w-3.5 h-3.5" /> Enable
                            </>
                          )}
                        </button>
                        {trigger.is_enabled && (
                          <button
                            onClick={() => handleFire(trigger.id)}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                          >
                            <PlayCircle className="w-3.5 h-3.5" />
                            Fire Now
                          </button>
                        )}
                        <hr className="my-1 border-slate-100" />
                        <button
                          onClick={() => handleDelete(trigger.id)}
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

      {/* Create modal */}
      {showCreate && (
        <CreateTriggerModal
          onClose={() => setShowCreate(false)}
          onCreated={fetchTriggers}
          workflowOptions={workflows}
        />
      )}
    </div>
  );
}
