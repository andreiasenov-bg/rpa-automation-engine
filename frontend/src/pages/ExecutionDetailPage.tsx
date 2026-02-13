/**
 * ExecutionDetailPage — Full execution detail view with step-by-step progress.
 *
 * Shows execution metadata, step timeline with status indicators,
 * live log viewer, and variable context.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
  Ban,
  Loader2,
  RotateCcw,
  Play,
  Timer,
  Hash,
  GitBranch,
  Server,
  Calendar,
  ChevronRight,
  Copy,
  ExternalLink,
} from 'lucide-react';
import type { Execution } from '@/types';
import { executionApi } from '@/api/executions';
import { useWebSocket, type ExecutionStatusPayload } from '@/hooks/useWebSocket';
import LiveLogViewer from '@/components/LiveLogViewer';
import { useLocale } from '@/i18n';

/* ─── Status config ─── */
const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; border: string; textColor: string }> = {
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800', textColor: 'text-amber-700 dark:text-amber-400' },
  running: { icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800', textColor: 'text-blue-700 dark:text-blue-400' },
  completed: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800', textColor: 'text-emerald-700 dark:text-emerald-400' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800', textColor: 'text-red-700 dark:text-red-400' },
  cancelled: { icon: Ban, color: 'text-slate-500', bg: 'bg-slate-50 dark:bg-slate-800', border: 'border-slate-200 dark:border-slate-700', textColor: 'text-slate-600 dark:text-slate-400' },
};

function StatusBadge({ status, large }: { status: string; large?: boolean }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${cfg.bg} ${cfg.color} ${cfg.border} ${large ? 'px-4 py-1.5 text-sm' : 'px-2.5 py-1 text-xs'}`}>
      <Icon className={large ? 'w-4 h-4' : 'w-3 h-3'} />
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

function formatDatetime(iso?: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

/* ─── Metadata card ─── */
function MetaItem({ icon: Icon, label, value, mono }: { icon: React.ElementType; label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</p>
        <p className={`text-sm text-slate-900 dark:text-white truncate ${mono ? 'font-mono text-xs' : ''}`}>{value}</p>
      </div>
    </div>
  );
}

/* ─── Step timeline ─── */
interface StepInfo {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

function StepTimeline({ steps }: { steps: StepInfo[] }) {
  if (steps.length === 0) {
    return (
      <div className="text-center py-8">
        <GitBranch className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-400">No step data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        const statusCfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.pending;
        const Icon = statusCfg.icon;

        return (
          <div key={step.id} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${statusCfg.bg} ${statusCfg.border} border`}>
                <Icon className={`w-3.5 h-3.5 ${statusCfg.color}`} />
              </div>
              {!isLast && <div className="w-px flex-1 bg-slate-200 dark:bg-slate-700 my-1" />}
            </div>

            {/* Step content */}
            <div className={`flex-1 pb-4 ${isLast ? '' : ''}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{step.name}</p>
                  <p className="text-[10px] text-slate-400 font-mono">{step.type}</p>
                </div>
                <div className="text-right">
                  <p className={`text-xs font-medium ${statusCfg.textColor}`}>{step.status}</p>
                  {step.duration_ms && (
                    <p className="text-[10px] text-slate-400">{formatDuration(step.duration_ms)}</p>
                  )}
                </div>
              </div>
              {step.error && (
                <div className="mt-1.5 text-[10px] text-red-500 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded px-2 py-1">
                  {step.error}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Main page ─── */
export default function ExecutionDetailPage() {
  const { t } = useLocale();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [steps, setSteps] = useState<StepInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const { on } = useWebSocket();

  const fetchExecution = useCallback(async () => {
    if (!id) return;
    try {
      const data = await executionApi.get(id);
      setExecution(data);

      // Try to extract step info from execution metadata
      const meta = (data as any).steps || (data as any).step_results || [];
      if (Array.isArray(meta) && meta.length > 0) {
        setSteps(meta.map((s: any) => ({
          id: s.id || s.step_id || `step_${Math.random()}`,
          name: s.name || s.step_name || s.type || 'Unknown',
          type: s.type || s.step_type || 'unknown',
          status: s.status || 'pending',
          started_at: s.started_at,
          completed_at: s.completed_at,
          duration_ms: s.duration_ms,
          error: s.error || s.error_message,
        })));
      }
    } catch {
      navigate('/executions');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchExecution();
  }, [fetchExecution]);

  // Live status updates
  useEffect(() => {
    const unsubscribe = on('execution.status_changed', (payload) => {
      const data = payload as ExecutionStatusPayload;
      if (data.execution_id === id) {
        setExecution((prev) => prev ? { ...prev, status: data.status as Execution['status'] } : prev);
      }
    });
    return unsubscribe;
  }, [id, on]);

  // Auto-refresh for running executions
  useEffect(() => {
    if (!execution || (execution.status !== 'running' && execution.status !== 'pending')) return;
    const interval = setInterval(fetchExecution, 5000);
    return () => clearInterval(interval);
  }, [execution, fetchExecution]);

  const handleRetry = async () => {
    if (!id) return;
    try {
      await executionApi.retry(id);
      fetchExecution();
    } catch { /* handle */ }
  };

  const handleCancel = async () => {
    if (!id) return;
    try {
      await executionApi.cancel(id);
      fetchExecution();
    } catch { /* handle */ }
  };

  const copyId = () => {
    if (id) navigator.clipboard.writeText(id);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!execution) return null;

  const isActive = execution.status === 'running' || execution.status === 'pending';
  const isFailed = execution.status === 'failed' || execution.status === 'cancelled';

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/executions')} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
          <ArrowLeft className="w-5 h-5 text-slate-500" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Execution Detail</h1>
            <StatusBadge status={execution.status} large />
          </div>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-xs font-mono text-slate-400">{id}</p>
            <button onClick={copyId} className="p-0.5 text-slate-400 hover:text-slate-600" title="Copy ID">
              <Copy className="w-3 h-3" />
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isFailed && (
            <button onClick={handleRetry}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition text-slate-600 dark:text-slate-300">
              <RotateCcw className="w-4 h-4" /> Retry
            </button>
          )}
          {isActive && (
            <button onClick={handleCancel}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition text-red-600 dark:text-red-400">
              <Ban className="w-4 h-4" /> Cancel
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: metadata + steps */}
        <div className="lg:col-span-1 space-y-6">
          {/* Metadata card */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">Execution Info</h3>
            <div className="space-y-3.5">
              <MetaItem icon={Hash} label="Execution ID" value={id || '—'} mono />
              <MetaItem icon={GitBranch} label="Workflow" value={execution.workflow_id} mono />
              {execution.agent_id && <MetaItem icon={Server} label="Agent" value={execution.agent_id} mono />}
              <MetaItem icon={Play} label="Trigger Type" value={execution.trigger_type} />
              <MetaItem icon={Calendar} label="Started" value={formatDatetime(execution.started_at)} />
              <MetaItem icon={Calendar} label="Completed" value={formatDatetime(execution.completed_at)} />
              <MetaItem icon={Timer} label="Duration" value={formatDuration(execution.duration_ms)} />
              {execution.retry_count > 0 && (
                <MetaItem icon={RotateCcw} label="Retries" value={String(execution.retry_count)} />
              )}
            </div>

            {execution.workflow_id && (
              <Link to={`/workflows/${execution.workflow_id}/edit`}
                className="flex items-center gap-1 mt-4 text-xs text-indigo-500 hover:text-indigo-600 transition">
                <ExternalLink className="w-3 h-3" /> View Workflow
              </Link>
            )}
          </div>

          {/* Step timeline */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">
              Step Progress {steps.length > 0 && `(${steps.filter((s) => s.status === 'completed').length}/${steps.length})`}
            </h3>
            <StepTimeline steps={steps} />
          </div>
        </div>

        {/* Right column: logs + error */}
        <div className="lg:col-span-2 space-y-6">
          {/* Error message */}
          {execution.error_message && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-700 dark:text-red-400">Execution Failed</p>
                  <p className="text-xs text-red-600 dark:text-red-400/80 mt-1 font-mono whitespace-pre-wrap">{execution.error_message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Live logs */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">Execution Logs</h3>
            <LiveLogViewer executionId={id!} isRunning={execution.status === 'running'} />
          </div>
        </div>
      </div>
    </div>
  );
}
