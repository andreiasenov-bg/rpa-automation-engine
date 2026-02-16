/**
 * WorkflowDetailPage — Clean dashboard for each RPA workflow.
 *
 * Shows: workflow info + icon, latest execution, results with download,
 * schedule overview (3× daily), and quick links.
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  FileJson,
  FileSpreadsheet,
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
  Database,
  Bot,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { storageApi } from '@/api/storage';
import { workflowApi } from '@/api/workflows';

/* ─── Workflow Icon Picker ─── */
const WORKFLOW_ICONS: Record<string, any> = {
  price: TrendingUp,
  comparison: TrendingUp,
  scrape: Globe,
  scraper: Globe,
  best: ShoppingCart,
  seller: ShoppingCart,
  tracker: BarChart3,
  monitor: Activity,
  smart: Bot,
  amazon: ShoppingCart,
  default: Zap,
};

function getWorkflowIcon(name: string) {
  const lower = name.toLowerCase();
  for (const [keyword, Icon] of Object.entries(WORKFLOW_ICONS)) {
    if (keyword !== 'default' && lower.includes(keyword)) return Icon;
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
function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatDuration(ms: number | null): string {
  if (!ms) return '—';
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  const min = Math.floor(ms / 60000);
  const sec = Math.round((ms % 60000) / 1000);
  return `${min}m ${sec}s`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusBadge(s: string) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    completed: { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-300', label: 'Completed' },
    running: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', label: 'Running' },
    failed: { bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-300', label: 'Failed' },
    pending: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-300', label: 'Pending' },
    cancelled: { bg: 'bg-slate-50 dark:bg-slate-900/20', text: 'text-slate-600 dark:text-slate-400', label: 'Cancelled' },
  };
  const cfg = map[s] || map.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full ${cfg.bg} ${cfg.text}`}>
      {s === 'completed' && <CheckCircle2 className="w-3 h-3" />}
      {s === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
      {s === 'failed' && <XCircle className="w-3 h-3" />}
      {cfg.label}
    </span>
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

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const resp = await storageApi.getWorkflowDetail(id);
      setDetail(resp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load workflow');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  const handleDownloadJSON = async () => {
    if (!id || !detail) return;
    setDownloading(true);
    try {
      await storageApi.downloadLatestResults(id, detail.workflow.name);
    } catch {
      alert('No results available to download.');
    } finally {
      setDownloading(false);
    }
  };

  const handleRun = async () => {
    if (!id) return;
    try {
      await workflowApi.execute(id);
      setTimeout(loadDetail, 2000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start execution');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-3xl mx-auto mt-12 p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-red-700 dark:text-red-300 font-medium">{error || 'Workflow not found'}</p>
          <button onClick={() => navigate('/workflows')} className="mt-4 text-sm text-indigo-600 hover:underline">
            ← Back to Workflows
          </button>
        </div>
      </div>
    );
  }

  const wf = detail.workflow;
  const exec = detail.latest_execution;
  const results = detail.results_summary;
  const schedules = detail.schedules || [];
  const Icon = getWorkflowIcon(wf.name);
  const gradient = getWorkflowColor(wf.name);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* ── Back + Refresh ── */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => navigate('/workflows')} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="flex items-center gap-2">
          <button onClick={loadDetail} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition" title="Refresh">
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </button>
          <Link to={`/workflows/${id}/edit`} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition">
            <Edit3 className="w-3.5 h-3.5" /> Editor
          </Link>
        </div>
      </div>

      {/* ── Header Card ── */}
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
              <span>{wf.step_count} steps</span>
              <span>•</span>
              <span>{detail.total_executions} executions</span>
            </div>
          </div>
          <button
            onClick={handleRun}
            className="flex-shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-white/20 hover:bg-white/30 backdrop-blur rounded-xl font-semibold transition text-sm"
          >
            <Play className="w-4 h-4" /> Run
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* ── Latest Execution ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
            <Timer className="w-4 h-4 text-indigo-500" /> Latest Execution
          </h2>
          {exec ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Status</span>
                {statusBadge(exec.status)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Started</span>
                <span className="text-sm text-slate-700 dark:text-slate-300">{formatDate(exec.started_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Completed</span>
                <span className="text-sm text-slate-700 dark:text-slate-300">{formatDate(exec.completed_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Duration</span>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{formatDuration(exec.duration_ms)}</span>
              </div>
              {exec.error_message && (
                <div className="mt-2 p-2.5 bg-red-50 dark:bg-red-900/20 rounded-lg text-xs text-red-700 dark:text-red-300">
                  {exec.error_message}
                </div>
              )}
              <Link
                to={`/executions/${exec.id}`}
                className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline mt-1"
              >
                View details →
              </Link>
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No executions yet</p>
          )}
        </div>

        {/* ── Results ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
            <BarChart3 className="w-4 h-4 text-emerald-500" /> Results
          </h2>
          {results ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Records</span>
                <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{results.total_items}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Updated</span>
                <span className="text-sm text-slate-700 dark:text-slate-300">{formatDate(results.saved_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Size</span>
                <span className="text-sm text-slate-700 dark:text-slate-300">{formatBytes(results.file_size)}</span>
              </div>

              {/* Period info */}
              {exec && (
                <div className="mt-2 p-3 bg-emerald-50 dark:bg-emerald-900/10 rounded-lg">
                  <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                    Data from {formatDate(exec.started_at)}
                  </p>
                </div>
              )}

              {/* Download Buttons */}
              <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                <button
                  onClick={handleDownloadJSON}
                  disabled={downloading}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white rounded-xl text-sm font-semibold transition shadow-sm"
                >
                  {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  Download Results
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <FileJson className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-400 italic">No results yet</p>
              <p className="text-xs text-slate-400 mt-1">Run the RPA to generate data</p>
            </div>
          )}
        </div>

        {/* ── Schedule ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
            <Calendar className="w-4 h-4 text-violet-500" /> Schedule
          </h2>
          {schedules.length > 0 ? (
            <div className="space-y-3">
              {schedules.map((s: any) => (
                <div key={s.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{s.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">{s.cron_expression} ({s.timezone})</p>
                    {s.next_run_at && (
                      <p className="text-xs text-violet-600 dark:text-violet-400 mt-1">
                        Next run: {formatDate(s.next_run_at)}
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                    s.is_enabled
                      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                      : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
                  }`}>
                    {s.is_enabled ? 'Active' : 'Paused'}
                  </span>
                </div>
              ))}
              <Link to="/schedules" className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                Manage schedules →
              </Link>
            </div>
          ) : (
            <div className="text-center py-4">
              <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-400 italic">No schedule set</p>
              <p className="text-xs text-slate-400 mt-1">Publish the workflow for automatic 3× daily schedule</p>
            </div>
          )}
        </div>

        {/* ── Quick Actions ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
            <Settings className="w-4 h-4 text-slate-500" /> Quick Actions
          </h2>
          <div className="space-y-2">
            <Link
              to={`/workflows/${id}/edit`}
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900/50 transition"
            >
              <div className="w-9 h-9 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
                <Edit3 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Edit Steps</p>
                <p className="text-xs text-slate-400">Open the visual editor</p>
              </div>
            </Link>
            <Link
              to="/executions"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900/50 transition"
            >
              <div className="w-9 h-9 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Execution History</p>
                <p className="text-xs text-slate-400">All {detail.total_executions} executions</p>
              </div>
            </Link>
            <Link
              to="/schedules"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900/50 transition"
            >
              <div className="w-9 h-9 bg-violet-100 dark:bg-violet-900/30 rounded-lg flex items-center justify-center">
                <Calendar className="w-4 h-4 text-violet-600 dark:text-violet-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Manage Schedules</p>
                <p className="text-xs text-slate-400">Set up automatic execution</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
