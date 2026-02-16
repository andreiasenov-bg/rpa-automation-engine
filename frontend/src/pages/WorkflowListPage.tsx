import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  Search,
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
  AlertCircle,
  AlertTriangle,
  Bug,
} from 'lucide-react';
import type { Workflow, Execution } from '@/types';
import { workflowApi } from '@/api/workflows';
import { executionApi } from '@/api/executions';

/* ─── Workflow type icon detection (most specific first) ─── */
function getWorkflowIcon(wf: Workflow): { icon: React.ElementType; bg: string; color: string } {
  const name = (wf.name || '').toLowerCase();
  const desc = (wf.description || '').toLowerCase();
  const steps = wf.definition?.steps || [];
  const stepTypes = steps.map((s) => s.type).join(' ');

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
  if (name.includes('scrape') || desc.includes('scrape') || stepTypes.includes('browser'))
    return { icon: FileSearch, bg: 'bg-purple-100', color: 'text-purple-600' };
  if (name.includes('quick'))
    return { icon: Zap, bg: 'bg-orange-100', color: 'text-orange-600' };
  return { icon: WorkflowIcon, bg: 'bg-indigo-100', color: 'text-indigo-600' };
}

/* ─── Time ago helper ─── */
function timeAgo(iso?: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

/* ─── Execution status badge for card ─── */
function LastRunBadge({ exec }: { exec?: Execution }) {
  if (!exec) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-slate-400">
        <Clock className="w-3 h-3" /> Never run
      </span>
    );
  }
  const cfg: Record<string, { icon: React.ElementType; cls: string; label: string }> = {
    completed: { icon: CheckCircle2, cls: 'text-emerald-600', label: 'Success' },
    failed: { icon: AlertCircle, cls: 'text-red-500', label: 'Failed' },
    running: { icon: Loader2, cls: 'text-blue-500', label: 'Running' },
    pending: { icon: Clock, cls: 'text-amber-500', label: 'Pending' },
    cancelled: { icon: XCircle, cls: 'text-slate-400', label: 'Cancelled' },
  };
  const c = cfg[exec.status] || cfg.pending;
  const Icon = c.icon;
  return (
    <div className="flex items-center justify-between">
      <span className={`inline-flex items-center gap-1 text-xs font-medium ${c.cls}`}>
        <Icon className={`w-3 h-3 ${exec.status === 'running' ? 'animate-spin' : ''}`} />
        {c.label}
      </span>
      <span className="text-[11px] text-slate-400">{timeAgo(exec.started_at || exec.completed_at)}</span>
    </div>
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
  const [latestExecs, setLatestExecs] = useState<Record<string, Execution>>({});
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

  const fetchLatestExecs = useCallback(async () => {
    try {
      const data = await executionApi.list(1, 100);
      const map: Record<string, Execution> = {};
      for (const exec of data.executions || []) {
        if (!map[exec.workflow_id]) map[exec.workflow_id] = exec;
      }
      setLatestExecs(map);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchWorkflows(); fetchLatestExecs(); }, [fetchWorkflows, fetchLatestExecs]);

  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 4000); return () => clearTimeout(t); }
  }, [toast]);

  useEffect(() => {
    if (actionMenu) {
      const handler = () => setActionMenu(null);
      setTimeout(() => document.addEventListener('click', handler), 0);
      return () => document.removeEventListener('click', handler);
    }
  }, [actionMenu]);

  const handleCreate = async () => {
    try {
      const wf = await workflowApi.create({ name: 'Untitled Workflow', description: '', definition: { steps: [], variables: {} } });
      navigate(`/workflows/${wf.id}/edit`);
    } catch { setToast({ type: 'error', message: 'Failed to create workflow' }); }
  };

  const handlePublish = async (id: string) => {
    try { await workflowApi.publish(id); setActionMenu(null); setToast({ type: 'success', message: 'Published!' }); fetchWorkflows(); }
    catch { setToast({ type: 'error', message: 'Failed to publish' }); }
  };

  const handleArchive = async (id: string) => {
    try { await workflowApi.archive(id); setActionMenu(null); setToast({ type: 'success', message: 'Archived' }); fetchWorkflows(); }
    catch { setToast({ type: 'error', message: 'Failed to archive' }); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this robot?')) return;
    try { await workflowApi.delete(id); setActionMenu(null); setToast({ type: 'success', message: 'Deleted' }); fetchWorkflows(); }
    catch { setToast({ type: 'error', message: 'Failed to delete' }); }
  };

  const handleExecute = async (id: string) => {
    setExecutingId(id);
    try {
      const result = await workflowApi.execute(id);
      setActionMenu(null);
      setToast({ type: 'success', message: 'Started! Redirecting...' });
      setTimeout(() => navigate(`/executions/${result?.id || ''}`), 800);
    } catch (e: any) {
      setToast({ type: 'error', message: e?.response?.data?.detail || 'Failed to execute' });
    } finally { setExecutingId(null); }
  };

  const filteredWorkflows = search
    ? workflows.filter((w) => w.name.toLowerCase().includes(search.toLowerCase()) || w.description?.toLowerCase().includes(search.toLowerCase()))
    : workflows;

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium ${toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'}`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">RPA Robots</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{total} robot{total !== 1 ? 's' : ''} total</p>
        </div>
        <div className="flex gap-2">
          <Link to="/create" className="inline-flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:border-indigo-300 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-lg transition">
            <Wand2 className="w-4 h-4 text-indigo-500" /> AI Create
          </Link>
          <button onClick={handleCreate} className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition">
            <Plus className="w-4 h-4" /> New Robot
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-5">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search robots..."
            className="w-full pl-9 pr-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition" />
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>
      ) : filteredWorkflows.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 px-5 py-16 text-center">
          <Bot className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">{search ? 'No robots match your search' : 'No robots yet'}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
            {search ? 'Try a different search term' : 'Create your first RPA robot manually or use AI to generate one'}
          </p>
          {!search && (
            <div className="flex gap-3 justify-center">
              <Link to="/create" className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 transition shadow-lg shadow-indigo-500/25">
                <Wand2 className="w-4 h-4" /> Create with AI
              </Link>
              <button onClick={handleCreate} className="inline-flex items-center gap-2 px-5 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-lg hover:bg-slate-50 transition">
                <Plus className="w-4 h-4" /> Blank Robot
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filteredWorkflows.map((wf) => {
              const { icon: WfIcon, bg, color } = getWorkflowIcon(wf);
              const lastExec = latestExecs[wf.id];
              return (
                <div key={wf.id}
                  className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-lg hover:shadow-indigo-500/5 transition-all cursor-pointer group relative"
                  onClick={() => navigate(`/workflows/${wf.id}/files`)}>

                  {/* Bug detected badge */}
                  {lastExec?.status === 'failed' && (
                    <div className="absolute top-3 left-3 z-10 flex items-center gap-1 px-2 py-1 bg-red-500 text-white text-[10px] font-bold rounded-full shadow-lg animate-pulse">
                      <Bug className="w-3 h-3" /> Bug
                    </div>
                  )}

                  {/* ··· menu */}
                  <div className="absolute top-3 right-3" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => setActionMenu(actionMenu === wf.id ? null : wf.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors opacity-0 group-hover:opacity-100">
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </button>
                    {actionMenu === wf.id && (
                      <div className="absolute right-0 top-8 z-20 w-44 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1">
                        <Link to={`/workflows/${wf.id}/edit`} className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700">
                          <Edit3 className="w-3.5 h-3.5" /> Edit
                        </Link>
                        {wf.status === 'published' && (
                          <button onClick={() => handleExecute(wf.id)} disabled={executingId === wf.id}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 w-full text-left disabled:opacity-50">
                            {executingId === wf.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Run
                          </button>
                        )}
                        {wf.status === 'draft' && (
                          <button onClick={() => handlePublish(wf.id)} className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 w-full text-left">
                            <Globe className="w-3.5 h-3.5" /> Publish
                          </button>
                        )}
                        {wf.status !== 'archived' && (
                          <button onClick={() => handleArchive(wf.id)} className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 w-full text-left">
                            <Archive className="w-3.5 h-3.5" /> Archive
                          </button>
                        )}
                        <hr className="my-1 border-slate-100 dark:border-slate-700" />
                        <button onClick={() => handleDelete(wf.id)} className="flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 w-full text-left">
                          <Trash2 className="w-3.5 h-3.5" /> Delete
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Icon */}
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${bg} mb-4`}>
                    <WfIcon className={`w-7 h-7 ${color}`} />
                  </div>

                  {/* Name */}
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1 pr-8 line-clamp-1">{wf.name}</h3>

                  {/* Description */}
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-4 min-h-[2rem]">
                    {wf.description || 'No description'}
                  </p>

                  {/* Last run + status */}
                  <div className="border-t border-slate-100 dark:border-slate-700 pt-3 space-y-2">
                    <LastRunBadge exec={lastExec} />
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                        wf.status === 'published' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : wf.status === 'archived' ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}>{wf.status}</span>
                      <span className="text-[10px] text-slate-400">{wf.definition?.steps?.length || 0} steps</span>
                    </div>
                  </div>

                  {/* Open button */}
                  <button className="mt-4 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition"
                    onClick={(e) => { e.stopPropagation(); navigate(`/workflows/${wf.id}/files`); }}>
                    <Eye className="w-3.5 h-3.5" /> Open
                  </button>
                </div>
              );
            })}
          </div>

          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <p className="text-xs text-slate-500 dark:text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700 transition">Previous</button>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700 transition">Next</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
