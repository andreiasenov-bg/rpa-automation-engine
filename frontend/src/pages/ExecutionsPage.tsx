import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Play,
  RefreshCw,
  XCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Ban,
  Activity,
  RotateCcw,
  Wifi,
  WifiOff,
  ExternalLink,
  Globe,
  Code2,
  MousePointerClick,
  FileSearch,
  Timer,
  Zap,
  GitBranch,
  Hash,
} from 'lucide-react';
import type { Execution, ExecutionLog, Workflow } from '@/types';
import { executionApi } from '@/api/executions';
import { workflowApi } from '@/api/workflows';
import { exportApi } from '@/api/export';
import { useWebSocket, type ExecutionStatusPayload } from '@/hooks/useWebSocket';
import { useLocale } from '@/i18n';
import LiveLogViewer from '@/components/LiveLogViewer';

/* ─── Status config ─── */
const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; border: string; label: string }> = {
  pending:   { icon: Clock,        color: 'text-amber-600',   bg: 'bg-amber-50',   border: 'border-amber-200',   label: 'Pending' },
  running:   { icon: Activity,     color: 'text-blue-600',    bg: 'bg-blue-50',    border: 'border-blue-200',    label: 'Running' },
  completed: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Completed' },
  failed:    { icon: XCircle,      color: 'text-red-600',     bg: 'bg-red-50',     border: 'border-red-200',     label: 'Failed' },
  cancelled: { icon: Ban,          color: 'text-slate-500',   bg: 'bg-slate-50',   border: 'border-slate-200',   label: 'Cancelled' },
};

/* ─── Trigger type icons ─── */
const TRIGGER_ICON: Record<string, React.ElementType> = {
  manual: MousePointerClick,
  schedule: Timer,
  webhook: Zap,
  api: Code2,
  retry: RotateCcw,
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function TriggerBadge({ type }: { type: string }) {
  const Icon = TRIGGER_ICON[type] || Zap;
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
      <Icon className="w-3 h-3" />
      {type}
    </span>
  );
}

function formatDuration(ms?: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function formatTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + ', ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatTimeAgo(iso?: string): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/* ─── Execution row ─── */
function ExecutionRow({
  execution,
  workflowName,
  onRetry,
  onCancel,
}: {
  execution: Execution;
  workflowName: string;
  onRetry: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isActive = execution.status === 'running' || execution.status === 'pending';

  return (
    <div className={`border-b border-slate-100 last:border-0 ${isActive ? 'bg-blue-50/30' : ''}`}>
      <div
        className="px-5 py-3.5 flex items-center gap-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-slate-400 flex-shrink-0">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Workflow icon based on status */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          execution.status === 'completed' ? 'bg-emerald-100' :
          execution.status === 'failed' ? 'bg-red-100' :
          execution.status === 'running' ? 'bg-blue-100' :
          execution.status === 'cancelled' ? 'bg-slate-100' :
          'bg-amber-100'
        }`}>
          {execution.status === 'running' ? (
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          ) : execution.status === 'completed' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : execution.status === 'failed' ? (
            <XCircle className="w-4 h-4 text-red-600" />
          ) : (
            <GitBranch className="w-4 h-4 text-slate-500" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-900 truncate">
            {workflowName || 'Unknown Workflow'}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-400 font-mono">
              <Hash className="w-2.5 h-2.5" />
              {execution.id.slice(0, 8)}
            </span>
            <span className="text-slate-300">·</span>
            <TriggerBadge type={execution.trigger_type} />
            <span className="text-slate-300">·</span>
            <span className="text-[11px] text-slate-400">{formatTimeAgo(execution.started_at)}</span>
          </div>
        </div>

        {/* Duration with icon */}
        <div className="flex items-center gap-1.5 text-xs text-slate-500 flex-shrink-0 bg-slate-50 px-2 py-1 rounded-md">
          <Timer className="w-3 h-3 text-slate-400" />
          {formatDuration(execution.duration_ms)}
        </div>

        {execution.retry_count > 0 && (
          <span className="inline-flex items-center gap-1 text-[10px] bg-amber-50 text-amber-600 border border-amber-200 px-1.5 py-0.5 rounded-full">
            <RotateCcw className="w-2.5 h-2.5" />
            #{execution.retry_count}
          </span>
        )}

        <StatusBadge status={execution.status} />

        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Link
            to={`/executions/${execution.id}`}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-indigo-600 transition-colors"
            title="View details"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
          {(execution.status === 'failed' || execution.status === 'cancelled') && (
            <button
              onClick={() => onRetry(execution.id)}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-indigo-600 transition-colors"
              title="Retry"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
          {(execution.status === 'pending' || execution.status === 'running') && (
            <button
              onClick={() => onCancel(execution.id)}
              className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
              title="Cancel"
            >
              <Ban className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="px-5 pb-4 pl-14 space-y-3">
          {/* Execution meta info */}
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3 h-3" /> Started: {formatTime(execution.started_at)}
            </span>
            {execution.completed_at && (
              <span className="inline-flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Ended: {formatTime(execution.completed_at)}
              </span>
            )}
          </div>
          {execution.error_message && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg px-3 py-2">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>{execution.error_message}</span>
            </div>
          )}
          <LiveLogViewer executionId={execution.id} isRunning={execution.status === 'running'} />
        </div>
      )}
    </div>
  );
}

/* ─── Main page ─── */
export default function ExecutionsPage() {
  const { t } = useLocale();
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [workflowNames, setWorkflowNames] = useState<Record<string, string>>({});
  const perPage = 25;

  const { readyState, on } = useWebSocket();

  // Fetch workflow names for lookup
  useEffect(() => {
    const fetchNames = async () => {
      try {
        const data = await workflowApi.list(1, 100);
        const nameMap: Record<string, string> = {};
        (data.workflows || []).forEach((w: Workflow) => { nameMap[w.id] = w.name; });
        setWorkflowNames(nameMap);
      } catch { /* ignore */ }
    };
    fetchNames();
  }, []);

  const fetchExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const filters: { status?: string } = {};
      if (statusFilter) filters.status = statusFilter;
      const data = await executionApi.list(page, perPage, filters);
      setExecutions(data.executions || []);
      setTotal(data.total || 0);
    } catch {
      setExecutions([]);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => { fetchExecutions(); }, [fetchExecutions]);

  const fetchRef = useRef(fetchExecutions);
  fetchRef.current = fetchExecutions;

  useEffect(() => {
    const hasRunning = executions.some((e) => e.status === 'running' || e.status === 'pending');
    if (!hasRunning) return;
    const interval = setInterval(() => fetchRef.current(), 5000);
    return () => clearInterval(interval);
  }, [executions]);

  useEffect(() => {
    const unsubscribe = on('execution.status_changed', (payload) => {
      const data = payload as ExecutionStatusPayload;
      setExecutions((prev) =>
        prev.map((ex) =>
          ex.id === data.execution_id
            ? { ...ex, status: data.status as Execution['status'] }
            : ex
        )
      );
    });
    return unsubscribe;
  }, [on]);

  const handleRetry = async (id: string) => {
    try { await executionApi.retry(id); fetchExecutions(); } catch { /* */ }
  };
  const handleCancel = async (id: string) => {
    try { await executionApi.cancel(id); fetchExecutions(); } catch { /* */ }
  };

  const totalPages = Math.ceil(total / perPage);

  // Status filter counts
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    executions.forEach((e) => { counts[e.status] = (counts[e.status] || 0) + 1; });
    return counts;
  }, [executions]);

  const statusOptions = [
    { key: '', label: 'All', icon: Activity },
    { key: 'pending', label: 'Pending', icon: Clock },
    { key: 'running', label: 'Running', icon: Loader2 },
    { key: 'completed', label: 'Completed', icon: CheckCircle2 },
    { key: 'failed', label: 'Failed', icon: XCircle },
    { key: 'cancelled', label: 'Cancelled', icon: Ban },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('executions.title')}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} execution{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-400" title={`WebSocket: ${readyState}`}>
            {readyState === 'open' ? (
              <><Wifi className="w-3.5 h-3.5 text-emerald-500" /> Live</>
            ) : (
              <><WifiOff className="w-3.5 h-3.5 text-slate-400" /> Offline</>
            )}
          </span>
          <button
            onClick={() => exportApi.executions('csv', statusFilter ? { status: statusFilter } : undefined)}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition"
            title="Export to CSV"
          >
            {t('common.export')}
          </button>
          <button
            onClick={fetchExecutions}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </div>

      {/* Filters with icons */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex items-center gap-1.5 bg-white rounded-lg border border-slate-200 p-1">
          {statusOptions.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.key}
                onClick={() => { setStatusFilter(s.key); setPage(1); }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  statusFilter === s.key ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-3 h-3 ${statusFilter === s.key && s.key === 'running' ? 'animate-spin' : ''}`} />
                {s.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* List */}
      {loading && executions.length === 0 ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : executions.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <Play className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">No executions found</p>
          <Link
            to="/workflows"
            className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            Go to Workflows
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200">
          {executions.map((exec) => (
            <ExecutionRow
              key={exec.id}
              execution={exec}
              workflowName={workflowNames[exec.workflow_id] || ''}
              onRetry={handleRetry}
              onCancel={handleCancel}
            />
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
