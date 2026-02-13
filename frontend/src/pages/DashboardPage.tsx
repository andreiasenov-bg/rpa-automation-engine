import { useEffect, useState } from 'react';
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
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';

interface DashboardStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  running_executions: number;
  completed_executions: number;
  failed_executions: number;
}

interface RecentExecution {
  id: string;
  workflow_name: string;
  status: string;
  started_at: string;
  duration_ms?: number;
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  to,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
  to?: string;
}) {
  const content = (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5 text-white" />
        </div>
        <span className="text-sm text-slate-500">{label}</span>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );

  if (to) {
    return <Link to={to}>{content}</Link>;
  }
  return content;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    running: 'bg-blue-50 text-blue-700 border-blue-200',
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
    failed: 'bg-red-50 text-red-700 border-red-200',
    cancelled: 'bg-slate-50 text-slate-600 border-slate-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        styles[status] || styles.pending
      }`}
    >
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
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return d.toLocaleDateString();
}

export default function DashboardPage() {
  const { t } = useLocale();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<RecentExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch stats and recent executions in parallel
        const [statsRes, execRes] = await Promise.all([
          client.get('/dashboard/stats').catch(() => null),
          client.get('/executions/', { params: { per_page: 10 } }).catch(() => null),
        ]);

        if (statsRes?.data) {
          setStats(statsRes.data);
        } else {
          // Fallback: derive from individual calls
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
        // Graceful: show zeros
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
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('dashboard.title')}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard
          icon={GitBranch}
          label={t('dashboard.totalWorkflows')}
          value={stats?.total_workflows ?? 0}
          color="bg-indigo-500"
          to="/workflows"
        />
        <StatCard
          icon={TrendingUp}
          label={t('dashboard.activeWorkflows')}
          value={stats?.active_workflows ?? 0}
          color="bg-emerald-500"
        />
        <StatCard
          icon={Play}
          label={t('dashboard.totalExecutions')}
          value={stats?.total_executions ?? 0}
          color="bg-blue-500"
          to="/executions"
        />
        <StatCard
          icon={Clock}
          label={t('dashboard.running')}
          value={stats?.running_executions ?? 0}
          color="bg-amber-500"
        />
        <StatCard
          icon={CheckCircle2}
          label={t('dashboard.completed')}
          value={stats?.completed_executions ?? 0}
          color="bg-emerald-500"
        />
        <StatCard
          icon={XCircle}
          label={t('dashboard.failed')}
          value={stats?.failed_executions ?? 0}
          color="bg-red-500"
        />
      </div>

      {/* Recent Executions */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">{t('dashboard.recentExecutions')}</h2>
          <Link to="/executions" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            View all
          </Link>
        </div>

        {recent.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <AlertTriangle className="w-8 h-8 text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No executions yet. Create a workflow to get started.</p>
            <Link
              to="/workflows"
              className="inline-flex items-center gap-1.5 mt-3 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
            >
              <GitBranch className="w-4 h-4" />
              Go to Workflows
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {recent.map((exec) => (
              <div key={exec.id} className="px-5 py-3.5 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {exec.workflow_name || exec.id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">{formatTime(exec.started_at)}</p>
                </div>
                <div className="text-xs text-slate-500">{formatDuration(exec.duration_ms)}</div>
                <StatusBadge status={exec.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
