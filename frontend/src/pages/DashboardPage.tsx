import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  GitBranch,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  TrendingUp,
  Activity,
  Server,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  RefreshCw,
  Plus,
  Wifi,
  WifiOff,
  Shield,
  Layers,
  Timer,
  CalendarDays,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';
import { useWebSocket } from '@/hooks/useWebSocket';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';
import ActivityTimeline from '@/components/ActivityTimeline';

interface DashboardStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  running_executions: number;
  completed_executions: number;
  failed_executions: number;
  pending_executions?: number;
  avg_duration_ms?: number;
  success_rate?: number;
  agents_online?: number;
  agents_total?: number;
  schedules_active?: number;
}

interface RecentExecution {
  id: string;
  workflow_name: string;
  workflow_id?: string;
  status: string;
  started_at: string;
  duration_ms?: number;
  trigger_type?: string;
}

/* ─── Stat Card ─── */
function StatCard({
  icon: Icon,
  label,
  value,
  color,
  to,
  trend,
  suffix,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  color: string;
  to?: string;
  trend?: 'up' | 'down' | 'flat';
  suffix?: string;
}) {
  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-red-500' : 'text-slate-400';

  const content = (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow group">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5 text-white" />
        </div>
        {trend && <TrendIcon className={`w-4 h-4 ${trendColor}`} />}
      </div>
      <div className="text-2xl font-bold text-slate-900 dark:text-white">
        {value}{suffix && <span className="text-sm font-normal text-slate-400 ml-1">{suffix}</span>}
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{label}</p>
    </div>
  );

  if (to) {
    return <Link to={to} className="block">{content}</Link>;
  }
  return content;
}

/* ─── Status Badge ─── */
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
    running: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800',
    pending: 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800',
    failed: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800',
    cancelled: 'bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-600',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

/* ─── Success Rate Ring ─── */
function SuccessRateRing({ rate }: { rate: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (rate / 100) * circumference;
  const color = rate >= 90 ? '#10b981' : rate >= 70 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative w-28 h-28 mx-auto">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="currentColor" strokeWidth="6" className="text-slate-100 dark:text-slate-700" />
        <circle cx="50" cy="50" r={radius} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
          style={{ transition: 'stroke-dashoffset 1s ease' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-slate-900 dark:text-white">{rate}%</span>
        <span className="text-[10px] text-slate-400">success</span>
      </div>
    </div>
  );
}

/* ─── Quick Action Button ─── */
function QuickAction({ icon: Icon, label, to, color }: { icon: React.ElementType; label: string; to: string; color: string }) {
  return (
    <Link to={to} className="flex flex-col items-center gap-2 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700/50 transition group">
      <div className={`w-10 h-10 rounded-xl ${color} flex items-center justify-center group-hover:scale-105 transition-transform`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <span className="text-xs font-medium text-slate-600 dark:text-slate-300 text-center">{label}</span>
    </Link>
  );
}

/* ─── Helpers ─── */
function formatDuration(ms?: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function formatTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return d.toLocaleDateString();
}

/* ─── System Health Widget ─── */
function SystemHealth({ stats, wsState }: { stats: DashboardStats; wsState: string }) {
  const items = [
    {
      label: 'WebSocket',
      status: wsState === 'open' ? 'healthy' : 'degraded',
      icon: wsState === 'open' ? Wifi : WifiOff,
      detail: wsState === 'open' ? 'Connected' : 'Disconnected',
    },
    {
      label: 'Agents',
      status: (stats.agents_online ?? 0) > 0 ? 'healthy' : 'warning',
      icon: Server,
      detail: `${stats.agents_online ?? 0}/${stats.agents_total ?? 0} online`,
    },
    {
      label: 'Queue',
      status: (stats.pending_executions ?? 0) > 10 ? 'warning' : 'healthy',
      icon: Layers,
      detail: `${stats.pending_executions ?? 0} pending`,
    },
    {
      label: 'Schedules',
      status: 'healthy',
      icon: CalendarDays,
      detail: `${stats.schedules_active ?? 0} active`,
    },
  ];

  const statusColors: Record<string, string> = {
    healthy: 'bg-emerald-500',
    warning: 'bg-amber-500',
    degraded: 'bg-red-500',
  };

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${statusColors[item.status]}`} />
          <item.icon className="w-4 h-4 text-slate-400" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-700 dark:text-slate-200">{item.label}</p>
          </div>
          <span className="text-[10px] text-slate-400">{item.detail}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Main page ─── */
export default function DashboardPage() {
  const { t } = useLocale();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<RecentExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const { readyState } = useWebSocket();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, execRes] = await Promise.all([
          client.get('/dashboard/stats').catch(() => null),
          client.get('/executions/', { params: { per_page: 10 } }).catch(() => null),
        ]);

        if (statsRes?.data) {
          setStats(statsRes.data);
        } else {
          const [wfRes, exRes] = await Promise.all([
            client.get('/workflows/', { params: { per_page: 1 } }).catch(() => ({ data: { total: 0 } })),
            client.get('/executions/', { params: { per_page: 1 } }).catch(() => ({ data: { total: 0 } })),
          ]);
          setStats({
            total_workflows: wfRes.data.total || 0,
            active_workflows: 0,
            total_executions: exRes.data.total || 0,
            running_executions: 0,
            completed_executions: 0,
            failed_executions: 0,
          });
        }

        if (execRes?.data?.executions) {
          setRecent(execRes.data.executions.slice(0, 10));
        }
      } catch {
        setStats({
          total_workflows: 0,
          active_workflows: 0,
          total_executions: 0,
          running_executions: 0,
          completed_executions: 0,
          failed_executions: 0,
        });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const successRate = useMemo(() => {
    if (!stats) return 0;
    const total = stats.completed_executions + stats.failed_executions;
    if (total === 0) return 100;
    return Math.round((stats.completed_executions / total) * 100);
  }, [stats]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Activity className="w-6 h-6 text-indigo-500 animate-pulse" />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('dashboard.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
            {readyState === 'open' ? (
              <><Wifi className="w-3.5 h-3.5 text-emerald-500" /> Live</>
            ) : (
              <><WifiOff className="w-3.5 h-3.5 text-slate-400" /> Offline</>
            )}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard icon={GitBranch} label={t('dashboard.totalWorkflows')} value={stats?.total_workflows ?? 0} color="bg-indigo-500" to="/workflows" />
        <StatCard icon={TrendingUp} label={t('dashboard.activeWorkflows')} value={stats?.active_workflows ?? 0} color="bg-emerald-500" />
        <StatCard icon={Play} label={t('dashboard.totalExecutions')} value={stats?.total_executions ?? 0} color="bg-blue-500" to="/executions" />
        <StatCard icon={Clock} label={t('dashboard.running')} value={stats?.running_executions ?? 0} color="bg-amber-500" />
        <StatCard icon={CheckCircle2} label={t('dashboard.completed')} value={stats?.completed_executions ?? 0} color="bg-emerald-500" />
        <StatCard icon={XCircle} label={t('dashboard.failed')} value={stats?.failed_executions ?? 0} color="bg-red-500" />
      </div>

      {/* Middle row: Quick Actions + Success Rate + System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Quick Actions */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" /> Quick Actions
          </h3>
          <div className="grid grid-cols-3 gap-2">
            <QuickAction icon={Plus} label="New Workflow" to="/workflows" color="bg-indigo-500" />
            <QuickAction icon={Play} label="Executions" to="/executions" color="bg-blue-500" />
            <QuickAction icon={Server} label="Agents" to="/agents" color="bg-violet-500" />
            <QuickAction icon={Shield} label="Credentials" to="/credentials" color="bg-emerald-500" />
            <QuickAction icon={CalendarDays} label="Schedules" to="/schedules" color="bg-amber-500" />
            <QuickAction icon={Sparkles} label="Templates" to="/templates" color="bg-pink-500" />
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Success Rate
          </h3>
          <SuccessRateRing rate={successRate} />
          <div className="flex justify-center gap-6 mt-4">
            <div className="text-center">
              <p className="text-lg font-bold text-emerald-600">{stats?.completed_executions ?? 0}</p>
              <p className="text-[10px] text-slate-400">Passed</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-red-500">{stats?.failed_executions ?? 0}</p>
              <p className="text-[10px] text-slate-400">Failed</p>
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-500" /> System Health
          </h3>
          {stats && <SystemHealth stats={stats} wsState={readyState} />}
          {stats?.avg_duration_ms && (
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700">
              <div className="flex items-center gap-2">
                <Timer className="w-4 h-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Avg Duration</p>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{formatDuration(stats.avg_duration_ms)}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Executions — now clickable rows */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">{t('dashboard.recentExecutions')}</h2>
          <Link to="/executions" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            View all
          </Link>
        </div>

        {recent.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <AlertTriangle className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No executions yet. Create a workflow to get started.</p>
            <Link to="/workflows" className="inline-flex items-center gap-1.5 mt-3 text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              <GitBranch className="w-4 h-4" /> Go to Workflows
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {recent.map((exec) => (
              <Link
                key={exec.id}
                to={`/executions/${exec.id}`}
                className="px-5 py-3.5 flex items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                    {exec.workflow_name || exec.id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {exec.trigger_type && <span className="capitalize">{exec.trigger_type} · </span>}
                    {formatTime(exec.started_at)}
                  </p>
                </div>
                <div className="text-xs text-slate-500">{formatDuration(exec.duration_ms)}</div>
                <StatusBadge status={exec.status} />
                <ChevronRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-indigo-500 transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Analytics section */}
      <div className="mt-8">
        <AnalyticsDashboard />
      </div>

      {/* Activity Timeline */}
      <div className="mt-8 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-4">{t('activity.title')}</h2>
        <ActivityTimeline days={7} limit={20} />
      </div>
    </div>
  );
}
