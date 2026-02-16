import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  Search,
  GitBranch,
  MoreHorizontal,
  Play,
  Archive,
  Trash2,
  Edit3,
  Globe,
  Loader2,
  Wand2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
  Copy,
  Eye,
  Bot,
  Code2,
  MousePointerClick,
  FileSearch,
  Database,
  Send,
  ShoppingCart,
  BarChart3,
  Shield,
  Workflow as WorkflowIcon,
  Zap,
  FolderOpen,
} from 'lucide-react';
import type { Workflow } from '@/types';
import { workflowApi } from '@/api/workflows';

/* ─── Workflow type icon detection (most specific first) ─── */
function getWorkflowIcon(wf: Workflow): { icon: React.ElementType; bg: string; color: string } {
  const name = (wf.name || '').toLowerCase();
  const desc = (wf.description || '').toLowerCase();
  const steps = wf.definition?.steps || [];
  const stepTypes = steps.map((s) => s.type).join(' ');

  // Most specific keyword matches first (name takes priority)
  if (name.includes('price') || name.includes('vergleich') || name.includes('comparison'))
    return { icon: ShoppingCart, bg: 'bg-amber-100', color: 'text-amber-600' };
  if (name.includes('best seller') || name.includes('tracker') || name.includes('track'))
    return { icon: BarChart3, bg: 'bg-emerald-100', color: 'text-emerald-600' };
  if (name.includes('monitor') || name.includes('health') || name.includes('uptime'))
    return { icon: Shield, bg: 'bg-green-100', color: 'text-green-600' };
  if (name.includes('smart') || name.includes('ai') || name.includes('auto'))
    return { icon: Bot, bg: 'bg-violet-100', color: 'text-violet-600' };
  if (name.includes('ssl') || name.includes('certificate'))
    return { icon: Shield, bg: 'bg-teal-100', color: 'text-teal-600' };
  if (name.includes('form') || name.includes('submit'))
    return { icon: MousePointerClick, bg: 'bg-rose-100', color: 'text-rose-600' };
  if (name.includes('invoice') || name.includes('download'))
    return { icon: Database, bg: 'bg-cyan-100', color: 'text-cyan-600' };
  if (name.includes('email') || name.includes('send') || name.includes('notify'))
    return { icon: Send, bg: 'bg-sky-100', color: 'text-sky-600' };
  if (name.includes('api') || stepTypes.includes('http_request'))
    return { icon: Code2, bg: 'bg-blue-100', color: 'text-blue-600' };
  // Generic scraper/browser last
  if (name.includes('scrape') || desc.includes('scrape') || stepTypes.includes('browser'))
    return { icon: FileSearch, bg: 'bg-purple-100', color: 'text-purple-600' };
  if (name.includes('quick'))
    return { icon: Zap, bg: 'bg-orange-100', color: 'text-orange-600' };
  return { icon: WorkflowIcon, bg: 'bg-indigo-100', color: 'text-indigo-600' };
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600',
    published: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
    archived: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.draft}`}>
      {status}
    </span>
  );
}

export default function WorkflowListPage() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const perPage = 20;

  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await workflowApi.list(page, perPage);
      setWorkflows(data.workflows || []);
      setTotal(data.total || 0);
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchWorkflows(); }, [fetchWorkflows]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  // Close menu on outside click
  useEffect(() => {
    if (actionMenu) {
      const handler = () => setActionMenu(null);
      setTimeout(() => document.addEventListener('click', handler), 0);
      return () => document.removeEventListener('click', handler);
    }
  }, [actionMenu]);

  const handleCreate = async () => {
    try {
      const wf = await workflowApi.create({
        name: 'Untitled Workflow',
        description: '',
        definition: { steps: [], variables: {} },
      });
      navigate(`/workflows/${wf.id}/edit`);
    } catch {
      setToast({ type: 'error', message: 'Failed to create workflow' });
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await workflowApi.publish(id);
      setActionMenu(null);
      setToast({ type: 'success', message: 'Workflow published!' });
      fetchWorkflows();
    } catch {
      setToast({ type: 'error', message: 'Failed to publish' });
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await workflowApi.archive(id);
      setActionMenu(null);
      setToast({ type: 'success', message: 'Workflow archived' });
      fetchWorkflows();
    } catch {
      setToast({ type: 'error', message: 'Failed to archive' });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await workflowApi.delete(id);
      setActionMenu(null);
      setToast({ type: 'success', message: 'Workflow deleted' });
      fetchWorkflows();
    } catch {
      setToast({ type: 'error', message: 'Failed to delete' });
    }
  };

  const handleExecute = async (id: string) => {
    setExecutingId(id);
    try {
      const result = await workflowApi.execute(id);
      setActionMenu(null);
      setToast({ type: 'success', message: 'Workflow started! Redirecting to execution...' });
      setTimeout(() => {
        navigate(`/executions/${result?.id || ''}`);
      }, 800);
    } catch (e: any) {
      setToast({ type: 'error', message: e?.response?.data?.detail || 'Failed to execute' });
    } finally {
      setExecutingId(null);
    }
  };

  const filteredWorkflows = search
    ? workflows.filter(
        (w) =>
          w.name.toLowerCase().includes(search.toLowerCase()) ||
          w.description?.toLowerCase().includes(search.toLowerCase()),
      )
    : workflows;

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all ${
          toast.type === 'success'
            ? 'bg-emerald-600 text-white'
            : 'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Workflows</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {total} workflow{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/create"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-600 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-lg transition"
          >
            <Wand2 className="w-4 h-4 text-indigo-500" />
            AI Create
          </Link>
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            New Workflow
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search workflows..."
            className="w-full pl-9 pr-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : filteredWorkflows.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 px-5 py-16 text-center">
          <GitBranch className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            {search ? 'No workflows match your search' : 'No workflows yet'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
            {search
              ? 'Try a different search term'
              : 'Create your first workflow manually or use AI to generate one from a description'}
          </p>
          {!search && (
            <div className="flex gap-3 justify-center">
              <Link
                to="/create"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 transition shadow-lg shadow-indigo-500/25"
              >
                <Wand2 className="w-4 h-4" />
                Create with AI
              </Link>
              <button
                onClick={handleCreate}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition"
              >
                <Plus className="w-4 h-4" />
                Blank Workflow
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Version</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Steps</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Updated</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {filteredWorkflows.map((wf) => (
                <tr key={wf.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      {(() => {
                        const { icon: WfIcon, bg, color } = getWorkflowIcon(wf);
                        return (
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${bg}`}>
                            <WfIcon className={`w-4 h-4 ${color}`} />
                          </div>
                        );
                      })()}
                      <div className="min-w-0">
                        <Link
                          to={`/workflows/${wf.id}/edit`}
                          className="text-sm font-medium text-slate-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                        >
                          {wf.name}
                        </Link>
                        {wf.description && (
                          <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 truncate max-w-xs">{wf.description}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3.5"><StatusBadge status={wf.status} /></td>
                  <td className="px-5 py-3.5 text-sm text-slate-500 dark:text-slate-400">v{wf.version}</td>
                  <td className="px-5 py-3.5 text-sm text-slate-500 dark:text-slate-400">{wf.definition?.steps?.length || 0}</td>
                  <td className="px-5 py-3.5 text-sm text-slate-500 dark:text-slate-400">
                    {new Date(wf.updated_at).toLocaleDateString()}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Inline quick actions */}
                      {wf.status === 'published' && (
                        <button
                          onClick={() => handleExecute(wf.id)}
                          disabled={executingId === wf.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition disabled:opacity-50"
                          title="Run workflow"
                        >
                          {executingId === wf.id ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                          Run
                        </button>
                      )}
                      {wf.status === 'draft' && (
                        <button
                          onClick={() => handlePublish(wf.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition"
                          title="Publish workflow"
                        >
                          <Globe size={12} />
                          Publish
                        </button>
                      )}
                      <Link
                        to={`/workflows/${wf.id}/edit`}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        title="Edit"
                      >
                        <Edit3 size={14} />
                      </Link>

                      {/* More menu */}
                      <div className="relative">
                        <button
                          onClick={(e) => { e.stopPropagation(); setActionMenu(actionMenu === wf.id ? null : wf.id); }}
                          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        >
                          <MoreHorizontal className="w-4 h-4 text-slate-400" />
                        </button>
                        {actionMenu === wf.id && (
                          <div className="absolute right-0 top-8 z-20 w-44 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1"
                               onClick={(e) => e.stopPropagation()}>
                            <Link
                              to={`/workflows/${wf.id}/edit`}
                              className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
                            >
                              <Edit3 className="w-3.5 h-3.5" /> Edit
                            </Link>
                            <Link
                              to={`/workflows/${wf.id}/files`}
                              className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
                            >
                              <FolderOpen className="w-3.5 h-3.5" /> Files
                            </Link>
                            {wf.status !== 'archived' && (
                              <button
                                onClick={() => handleArchive(wf.id)}
                                className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 w-full text-left"
                              >
                                <Archive className="w-3.5 h-3.5" /> Archive
                              </button>
                            )}
                            <hr className="my-1 border-slate-100 dark:border-slate-700" />
                            <button
                              onClick={() => handleDelete(wf.id)}
                              className="flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 w-full text-left"
                            >
                              <Trash2 className="w-3.5 h-3.5" /> Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
              <p className="text-xs text-slate-500 dark:text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
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
