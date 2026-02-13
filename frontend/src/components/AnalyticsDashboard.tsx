/**
 * Analytics Dashboard — Recharts-powered execution analytics.
 *
 * Features:
 * - Execution timeline (area chart)
 * - Success rate gauge (radial bar)
 * - Workflow performance (bar chart)
 * - Period selector (7d / 30d / 90d)
 */

import { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
  Loader2,
  BarChart3,
} from 'lucide-react';
import {
  fetchExecutionOverview,
  fetchExecutionTimeline,
  fetchWorkflowPerformance,
  type ExecutionOverview,
  type ExecutionTimeline,
  type WorkflowPerformanceEntry,
} from '@/api/analytics';
import { useLocale } from '@/i18n';

/* ─── Colors ─── */
const COLORS = {
  primary: '#6366f1',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  muted: '#94a3b8',
  bg: '#f8fafc',
};

/* ─── Period selector ─── */
function PeriodSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (days: number) => void;
}) {
  const options = [
    { label: '7d', days: 7 },
    { label: '30d', days: 30 },
    { label: '90d', days: 90 },
  ];

  return (
    <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
      {options.map(({ label, days }) => (
        <button
          key={days}
          onClick={() => onChange(days)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
            value === days
              ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/* ─── KPI Card ─── */
function KpiCard({
  label,
  value,
  suffix,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${color}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      </div>
      <p className="text-xl font-bold text-slate-900 dark:text-white">
        {value}
        {suffix && <span className="text-sm font-normal text-slate-400 ml-1">{suffix}</span>}
      </p>
    </div>
  );
}

/* ─── Execution Timeline Chart ─── */
function TimelineChart({ data }: { data: ExecutionTimeline | null }) {
  if (!data || !data.timeline || data.timeline.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-sm text-slate-400">
        No timeline data available
      </div>
    );
  }

  const chartData = data.timeline.map((entry) => ({
    date: entry.timestamp
      ? new Date(entry.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric' })
      : '—',
    executions: entry.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <defs>
          <linearGradient id="colorExec" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3} />
            <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#f1f5f9',
            fontSize: '12px',
          }}
        />
        <Area
          type="monotone"
          dataKey="executions"
          stroke={COLORS.primary}
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#colorExec)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ─── Success Rate Donut ─── */
function SuccessRateDonut({ rate }: { rate: number }) {
  const data = [
    { name: 'Success', value: rate },
    { name: 'Failure', value: 100 - rate },
  ];

  return (
    <div className="relative w-32 h-32 mx-auto">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={38}
            outerRadius={55}
            startAngle={90}
            endAngle={-270}
            dataKey="value"
            strokeWidth={0}
          >
            <Cell fill={COLORS.success} />
            <Cell fill="#e2e8f0" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-bold text-slate-900 dark:text-white">
          {rate.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

/* ─── Workflow Performance Chart ─── */
function WorkflowPerformanceChart({ data }: { data: WorkflowPerformanceEntry[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-sm text-slate-400">
        No workflow data available
      </div>
    );
  }

  const chartData = data.slice(0, 8).map((wf) => ({
    name: wf.workflow_name.length > 16 ? wf.workflow_name.slice(0, 14) + '...' : wf.workflow_name,
    success: wf.success_count,
    failed: wf.failure_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#f1f5f9',
            fontSize: '12px',
          }}
        />
        <Bar dataKey="success" fill={COLORS.success} radius={[4, 4, 0, 0]} barSize={20} name="Success" />
        <Bar dataKey="failed" fill={COLORS.danger} radius={[4, 4, 0, 0]} barSize={20} name="Failed" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ─── Main Dashboard ─── */
export default function AnalyticsDashboard() {
  const { t } = useLocale();
  const [days, setDays] = useState(7);
  const [overview, setOverview] = useState<ExecutionOverview | null>(null);
  const [timeline, setTimeline] = useState<ExecutionTimeline | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowPerformanceEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [ov, tl, wf] = await Promise.all([
          fetchExecutionOverview(days).catch(() => null),
          fetchExecutionTimeline(days, days <= 7 ? 'day' : days <= 30 ? 'day' : 'week').catch(() => null),
          fetchWorkflowPerformance(days, 10).catch(() => null),
        ]);
        setOverview(ov);
        setTimeline(tl);
        setWorkflows(wf?.workflows || []);
      } catch {
        // graceful
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [days]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{t('analytics.title')}</h2>
        </div>
        <PeriodSelector value={days} onChange={setDays} />
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label={t('dashboard.totalExecutions')}
          value={overview?.total_executions ?? 0}
          icon={Activity}
          color="bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
        />
        <KpiCard
          label={t('dashboard.completed')}
          value={overview?.successful_executions ?? 0}
          icon={CheckCircle2}
          color="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
        />
        <KpiCard
          label={t('dashboard.failed')}
          value={overview?.failed_executions ?? 0}
          icon={XCircle}
          color="bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400"
        />
        <KpiCard
          label={t('analytics.avgDuration')}
          value={overview ? formatDuration(overview.average_duration_ms) : '—'}
          icon={Clock}
          color="bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
            {t('analytics.executionTimeline')}
          </h3>
          <TimelineChart data={timeline} />
        </div>

        {/* Success rate */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
            {t('analytics.successRate')}
          </h3>
          <SuccessRateDonut rate={overview?.success_rate ?? 0} />
          <p className="text-xs text-slate-400 mt-3">
            {overview?.successful_executions ?? 0} / {overview?.total_executions ?? 0}
          </p>
        </div>
      </div>

      {/* Workflow performance */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
          {t('analytics.workflowPerformance')}
        </h3>
        <WorkflowPerformanceChart data={workflows} />
      </div>
    </div>
  );
}
