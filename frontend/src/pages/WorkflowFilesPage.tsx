/**
 * Robot Detail Page — 3-tab interface for each RPA robot.
 * Tabs: Results | Settings | Schedule
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  FileJson,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Edit3,
  Calendar,
  Timer,
  BarChart3,
  Settings,
  Zap,
  TrendingUp,
  ShoppingCart,
  Globe,
  Bot,
  Activity,
  AlertCircle,
  Power,
  PowerOff,
  Trash2,
  Plus,
} from 'lucide-react';
import { storageApi } from '@/api/storage';
import { workflowApi } from '@/api/workflows';
import { executionApi } from '@/api/executions';
import { listSchedules, createSchedule, deleteSchedule, toggleSchedule, type Schedule, type ScheduleCreate } from '@/api/schedules';
import type { Execution } from '@/types';

/* ─── Icon Picker ─── */
const WORKFLOW_ICONS: Record<string, any> = {
  price: TrendingUp, comparison: TrendingUp, scrape: Globe, scraper: Globe,
  best: ShoppingCart, seller: ShoppingCart, tracker: BarChart3,
  monitor: Activity, smart: Bot, amazon: ShoppingCart, default: Zap,
};
function getWorkflowIcon(name: string) {
  const lower = name.toLowerCase();
  for (const [kw, Icon] of Object.entries(WORKFLOW_ICONS)) {
    if (kw !== 'default' && lower.includes(kw)) return Icon;
  }
  return WORKFLOW_ICONS.default;
}
function getWorkflowColor(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('price') || lower.includes('comparison')) return 'from-emerald-500 to-teal-600';
  if (lower.includes('best') || lower.includes('seller')) return 'from-violet-500 to-purple-600';
  if (lower.includes('smart') || lower.includes('ai')) return 'from-blue-500 to-indigo-600';
  if (lower.includes('scrape') || lower.includes('scraper')) return 'from-orange-500 to-amber-600';
  return 'from-indigo-500 to-blue-600';
}

/* ─── Helpers ─── */
function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function formatDuration(ms: number | null | undefined): string {
  if (!ms) return '—';
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}
function timeAgo(iso?: string | null): string {
  if (!iso) return '—';
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

function execStatusBadge(s: string) {
  const map: Record<string, { bg: string; text: string; label: string; icon: any }> = {
    completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Completed', icon: CheckCircle2 },
    running: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Running', icon: Loader2 },
    failed: { bg: 'bg-red-50', text: 'text-red-700', label: 'Failed', icon: XCircle },
    pending: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Pending', icon: Clock },
    cancelled: { bg: 'bg-slate-50', text: 'text-slate-600', label: 'Cancelled', icon: XCircle },
  };
  const cfg = map[s] || map.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full ${cfg.bg} ${cfg.text}`}>
      <Icon className={`w-3 h-3 ${s === 'running' ? 'animate-spin' : ''}`} /> {cfg.label}
    </span>
  );
}

/* ─── Tab types ─── */
type TabKey = 'results' | 'settings' | 'schedule';

/* ─── Create Schedule Modal ─── */
function CreateScheduleModal({ workflowId, workflowName, onClose, onCreated }: {
  workflowId: string; workflowName: string; onClose: () => void; onCreated: () => void;
}) {
  const [name, setName] = useState(`${workflowName} - Schedule`);
  const [cronExpr, setCronExpr] = useState('0 8,14,20 * * *');
  const [timezone, setTimezone] = useState('Europe/Sofia');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createSchedule({ workflow_id: workflowId, name, cron_expression: cronExpr, timezone } as ScheduleCreate);
      onCreated(); onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create schedule');
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-md space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">New Schedule</h2>
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
          <input type="text" required value={name} onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Cron Expression</label>
          <input type="text" required value={cronExpr} onChange={(e) => setCronExpr(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono outline-none focus:ring-2 focus:ring-indigo-500" />
          <p className="text-xs text-slate-400 mt-1">minute hour day month weekday</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Timezone</label>
          <select value={timezone} onChange={(e) => setTimezone(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="Europe/Sofia">Europe/Sofia</option>
            <option value="UTC">UTC</option>
            <option value="Europe/London">Europe/London</option>
            <option value="America/New_York">America/New_York</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition">Cancel</button>
          <button type="submit" disabled={saving}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-50 flex items-center gap-1.5">
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Create
          </button>
        </div>
      </form>
    </div>
  );
}

/* ─── Main Component ─── */
export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState<any>(null);
  const [downloading, setDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>('results');

  // Executions for Results tab
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [execTotal, setExecTotal] = useState(0);
  const [execPage, setExecPage] = useState(1);

  // Schedules for Schedule tab
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [showCreateSchedule, setShowCreateSchedule] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true); setError('');
    try {
      const resp = await storageApi.getWorkflowDetail(id);
      setDetail(resp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load');
    } finally { setLoading(false); }
  }, [id]);

  const loadExecutions = useCallback(async () => {
    if (!id) return;
    try {
      const data = await executionApi.list(execPage, 10, { workflow_id: id });
      setExecutions(data.executions || []);
      setExecTotal(data.total || 0);
    } catch { /* silent */ }
  }, [id, execPage]);

  const loadSchedules = useCallback(async () => {
    if (!id) return;
    try {
      const data = await listSchedules({ workflow_id: id });
      setSchedules(data.items || []);
    } catch { /* silent */ }
  }, [id]);

  useEffect(() => { loadDetail(); }, [loadDetail]);
  useEffect(() => { if (activeTab === 'results') loadExecutions(); }, [activeTab, loadExecutions]);
  useEffect(() => { if (activeTab === 'schedule') loadSchedules(); }, [activeTab, loadSchedules]);

  const handleDownload = async () => {
    if (!id || !detail) return;
    setDownloading(true);
    try { await storageApi.downloadLatestResults(id, detail.workflow.name); }
    catch { alert('No results available.'); }
    finally { setDownloading(false); }
  };

  const handleRun = async () => {
    if (!id) return;
    try { await workflowApi.execute(id); setTimeout(loadDetail, 2000); }
    catch (err: any) { alert(err.response?.data?.detail || 'Failed to start'); }
  };

  const handleToggleSchedule = async (schedId: string) => {
    try { await toggleSchedule(schedId); loadSchedules(); } catch { /* */ }
  };

  const handleDeleteSchedule = async (schedId: string) => {
    if (!confirm('Delete this schedule?')) return;
    try { await deleteSchedule(schedId); loadSchedules(); } catch { /* */ }
  };

  if (loading) return <div className="flex items-center justify-center h-96"><Loader2 className="w-8 h-8 animate-spin text-indigo-500" /></div>;

  if (error || !detail) {
    return (
      <div className="max-w-3xl mx-auto mt-12 p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-red-700 font-medium">{error || 'Robot not found'}</p>
          <button onClick={() => navigate('/workflows')} className="mt-4 text-sm text-indigo-600 hover:underline">← Back to RPA List</button>
        </div>
      </div>
    );
  }

  const wf = detail.workflow;
  const results = detail.results_summary;
  const latestExec = detail.latest_execution;
  const Icon = getWorkflowIcon(wf.name);
  const gradient = getWorkflowColor(wf.name);

  const tabs: { key: TabKey; label: string; icon: any }[] = [
    { key: 'results', label: 'Results', icon: BarChart3 },
    { key: 'settings', label: 'Settings', icon: Settings },
    { key: 'schedule', label: 'Schedule', icon: Calendar },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Back + Refresh */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => navigate('/workflows')} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition">
          <ArrowLeft className="w-4 h-4" /> Back to RPA List
        </button>
        <button onClick={loadDetail} className="p-2 rounded-lg hover:bg-slate-100 transition" title="Refresh">
          <RefreshCw className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Header Card */}
      <div className={`relative bg-gradient-to-br ${gradient} rounded-2xl p-6 text-white mb-6 shadow-lg`}>
        <div className="flex items-start gap-5">
          <div className="flex-shrink-0 w-16 h-16 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
            <Icon className="w-8 h-8" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold truncate">{wf.name}</h1>
            {wf.description && <p className="text-white/80 mt-1 text-sm line-clamp-2">{wf.description}</p>}
            <div className="flex items-center gap-4 mt-3 text-sm text-white/70">
              <span>v{wf.version}</span>
              <span>•</span>
              <span>{wf.step_count || wf.definition?.steps?.length || 0} steps</span>
              <span>•</span>
              <span>{detail.total_executions} executions</span>
            </div>
          </div>
          <button onClick={handleRun}
            className="flex-shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-white/20 hover:bg-white/30 backdrop-blur rounded-xl font-semibold transition text-sm">
            <Play className="w-4 h-4" /> Run
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
        <div className="flex gap-1">
          {tabs.map((t) => {
            const TabIcon = t.icon;
            const active = activeTab === t.key;
            return (
              <button key={t.key} onClick={() => setActiveTab(t.key)}
                className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
                  active ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}>
                <TabIcon className="w-4 h-4" /> {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ═══ Tab: Results ═══ */}
      {activeTab === 'results' && (
        <div className="space-y-6">
          {/* Results summary */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
              <BarChart3 className="w-4 h-4 text-emerald-500" /> Latest Results
            </h2>
            {results ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-3 bg-emerald-50 rounded-lg">
                    <p className="text-2xl font-bold text-emerald-600">{results.total_items}</p>
                    <p className="text-xs text-slate-500 mt-1">Records</p>
                  </div>
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-sm font-medium text-slate-700">{formatDate(results.saved_at)}</p>
                    <p className="text-xs text-slate-500 mt-1">Updated</p>
                  </div>
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-sm font-medium text-slate-700">{formatBytes(results.file_size)}</p>
                    <p className="text-xs text-slate-500 mt-1">Size</p>
                  </div>
                </div>
                <button onClick={handleDownload} disabled={downloading}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white rounded-xl text-sm font-semibold transition shadow-sm">
                  {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  Download Excel
                </button>
              </div>
            ) : (
              <div className="text-center py-6">
                <FileJson className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No results yet — run the robot to generate data</p>
              </div>
            )}
          </div>

          {/* Execution history */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
              <Activity className="w-4 h-4 text-blue-500" /> Execution History
              <span className="ml-auto text-xs font-normal text-slate-400">{execTotal} total</span>
            </h2>
            {executions.length > 0 ? (
              <>
                <div className="space-y-2">
                  {executions.map((ex) => (
                    <Link key={ex.id} to={`/executions/${ex.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition group">
                      <div className="flex items-center gap-3">
                        {execStatusBadge(ex.status)}
                        <span className="text-xs text-slate-500">{formatDate(ex.started_at)}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-400">{formatDuration(ex.duration_ms)}</span>
                        <span className="text-xs text-slate-400">{ex.trigger_type}</span>
                      </div>
                    </Link>
                  ))}
                </div>
                {execTotal > 10 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-xs text-slate-400">Page {execPage} of {Math.ceil(execTotal / 10)}</p>
                    <div className="flex gap-2">
                      <button onClick={() => setExecPage((p) => Math.max(1, p - 1))} disabled={execPage === 1}
                        className="px-3 py-1 text-xs rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition">Prev</button>
                      <button onClick={() => setExecPage((p) => p + 1)} disabled={execPage >= Math.ceil(execTotal / 10)}
                        className="px-3 py-1 text-xs rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition">Next</button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-400 text-center py-4">No executions yet</p>
            )}
          </div>
        </div>
      )}

      {/* ═══ Tab: Settings ═══ */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
              <Settings className="w-4 h-4 text-slate-500" /> Robot Information
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500">Name</label>
                <p className="text-sm font-medium text-slate-900 dark:text-white">{wf.name}</p>
              </div>
              <div>
                <label className="text-xs text-slate-500">Description</label>
                <p className="text-sm text-slate-700 dark:text-slate-300">{wf.description || 'No description'}</p>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-slate-500">Status</label>
                  <p className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      wf.status === 'published' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : wf.status === 'archived' ? 'bg-amber-50 text-amber-700 border-amber-200'
                      : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}>{wf.status}</span>
                  </p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Version</label>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">v{wf.version}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Steps</label>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{wf.step_count || wf.definition?.steps?.length || 0}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500">Created</label>
                  <p className="text-sm text-slate-700 dark:text-slate-300">{formatDate(wf.created_at)}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Updated</label>
                  <p className="text-sm text-slate-700 dark:text-slate-300">{formatDate(wf.updated_at)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">Actions</h2>
            <div className="flex flex-wrap gap-3">
              <Link to={`/workflows/${id}/edit`}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition">
                <Edit3 className="w-4 h-4" /> Open Editor
              </Link>
              {wf.status === 'draft' && (
                <button onClick={async () => { try { await workflowApi.publish(id!); loadDetail(); } catch {} }}
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition">
                  <Globe className="w-4 h-4" /> Publish
                </button>
              )}
              {wf.status === 'published' && (
                <button onClick={handleRun}
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition">
                  <Play className="w-4 h-4" /> Run Now
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ Tab: Schedule ═══ */}
      {activeTab === 'schedule' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                <Calendar className="w-4 h-4 text-violet-500" /> Schedules
              </h2>
              <button onClick={() => setShowCreateSchedule(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg transition">
                <Plus className="w-3.5 h-3.5" /> New Schedule
              </button>
            </div>

            {schedules.length > 0 ? (
              <div className="space-y-3">
                {schedules.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{s.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5 font-mono">{s.cron_expression} ({s.timezone})</p>
                      {s.next_run_at && (
                        <p className="text-xs text-violet-600 dark:text-violet-400 mt-1">Next: {formatDate(s.next_run_at)}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => handleToggleSchedule(s.id)} title={s.is_enabled ? 'Disable' : 'Enable'}
                        className={`p-1.5 rounded-lg transition ${s.is_enabled ? 'text-emerald-600 hover:bg-emerald-50' : 'text-slate-400 hover:bg-slate-100'}`}>
                        {s.is_enabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                      </button>
                      <button onClick={() => handleDeleteSchedule(s.id)} title="Delete"
                        className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 transition">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No schedules configured</p>
                <p className="text-xs text-slate-400 mt-1">Create a schedule to run this robot automatically</p>
              </div>
            )}
          </div>

          {showCreateSchedule && id && (
            <CreateScheduleModal
              workflowId={id}
              workflowName={wf.name}
              onClose={() => setShowCreateSchedule(false)}
              onCreated={loadSchedules}
            />
          )}
        </div>
      )}
    </div>
  );
}
