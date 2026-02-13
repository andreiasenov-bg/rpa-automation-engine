import { useEffect, useState, useCallback, useRef } from 'react';
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
} from 'lucide-react';
import type { Execution, ExecutionLog } from '@/types';
import { executionApi } from '@/api/executions';
import { exportApi } from '@/api/export';
import { useWebSocket, type ExecutionStatusPayload } from '@/hooks/useWebSocket';
import { useLocale } from '@/i18n';

/* ─── Status config ─── */
const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; border: string }> = {
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  running: { icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  completed: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
  cancelled: { icon: Ban, color: 'text-slate-500', bg: 'bg-slate-50', border: 'border-slate-200' },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
      <Icon className="w-3 h-3" />
      {status}
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
  return new Date(iso).toLocaleString();
}

/* ─── Log viewer ─── */
function LogViewer({ executionId }: { executionId: string }) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await executionApi.logs(executionId);
        setLogs(Array.isArray(data) ? data : []);
      } catch {
        setLogs([]);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [executionId]);

  const levelColor: Record<string, string> = {
    INFO: 'text-blue-500',
    WARNING: 'text-amber-500',
    ERROR: 'text-red-500',
    DEBUG: 'text-slate-400',
  };

  if (loading) {
    return (
      <div className="py-4 flex justify-center">
        <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
      </div>
    );
  }

  if (logs.length === 0) {
    return <p className="py-4 text-xs text-slate-400 text-center">No logs available</p>;
  }

  return (
    <div className="bg-slate-900 rounded-lg p-3 max-h-64 overflow-y-auto font-mono text-xs space-y-0.5">
      {logs.map((log) => (
        <div key={log.id} className="flex gap-2">
          <span className="text-slate-500 flex-shrink-0">
            {new Date(log.timestamp).toLocaleTimeString()}
          </span>
          <span className={`flex-shrink-0 w-14 ${levelColor[log.level] || 'text-slate-400'}`}>
            [{log.level}]
          </span>
          <span className="text-slate-200 break-all">{log.message}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Execution row ─── */
function ExecutionRow({
  execution,
  onRetry,
  onCancel,
}: {
  execution: Execution;
  onRetry: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="px-5 py-3.5 flex items-center gap-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-slate-400 flex-shrink-0">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-900 truncate">
            {execution.id.slice(0, 8)}...
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {execution.trigger_type} &middot; {formatTime(execution.started_at)}
          </p>
        </div>

        <div className="text-xs text-slate-500 flex-shrink-0">
          {formatDuration(execution.duration_ms)}
        </div>

        {execution.retry_count > 0 && (
          <span className="text-[10px] bg-amber-50 text-amber-600 border border-amber-200 px-1.5 py-0.5 rounded-full">
            retry #{execution.retry_count}
          </span>
        )}

        <StatusBadge status={execution.status} />

        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
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
          {execution.error_message && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg px-3 py-2">
              {execution.error_message}
            </div>
          )}
          <LogViewer executionId={execution.id} />
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
  const perPage = 25;

  // WebSocket: live execution status updates
  const { readyState, on } = useWebSocket();

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

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  // Auto-refresh every 5s if there are running executions
  const fetchRef = useRef(fetchExecutions);
  fetchRef.current = fetchExecutions;

  useEffect(() => {
    const hasRunning = executions.some((e) => e.status === 'running' || e.status === 'pending');
    if (!hasRunning) return;
    const interval = setInterval(() => fetchRef.current(), 5000);
    return () => clearInterval(interval);
  }, [executions]);

  // WebSocket: update execution status in-place when event arrives
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
    try {
      await executionApi.retry(id);
      fetchExecutions();
    } catch {
      // handle error
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await executionApi.cancel(id);
      fetchExecutions();
    } catch {
      // handle error
    }
  };

  const totalPages = Math.ceil(total / perPage);

  const statusOptions = ['', 'pending', 'running', 'completed', 'failed', 'cancelled'];

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

      {/* Filters */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex items-center gap-1.5 bg-white rounded-lg border border-slate-200 p-1">
          {statusOptions.map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1); }}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                statusFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-50'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
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
