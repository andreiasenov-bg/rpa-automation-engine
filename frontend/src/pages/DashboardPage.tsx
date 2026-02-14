import { useEffect, useState, useMemo, useCallback } from 'react';
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
  Plus,
  Wifi,
  WifiOff,
  Shield,
  Layers,
  Timer,
  CalendarDays,
  ChevronRight,
  Sparkles,
  Settings2,
  X,
  Eye,
  EyeOff,
  GripVertical,
  RotateCcw,
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';
import ContextualHelp from '@/components/help/ContextualHelp';
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

/* ─── Widget config ─── */
type WidgetId = 'stats' | 'quickActions' | 'successRate' | 'systemHealth' | 'recentExecutions' | 'analytics' | 'activity';

interface WidgetConfig {
  id: WidgetId;
  label: string;
  visible: boolean;
}

const DEFAULT_WIDGETS: WidgetConfig[] = [
  { id: 'stats', label: 'Statistics Cards', visible: true },
  { id: 'quickActions', label: 'Quick Actions', visible: true },
  { id: 'successRate', label: 'Success Rate', visible: true },
  { id: 'systemHealth', label: 'System Health', visible: true },
  { id: 'recentExecutions', label: 'Recent Executions', visible: true },
  { id: 'analytics', label: 'Analytics Charts', visible: true },
  { id: 'activity', label: 'Activity Timeline', visible: true },
];

const STORAGE_KEY = 'rpa_dashboard_widgets';

function loadWidgets(): WidgetConfig[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return DEFAULT_WIDGETS;
    const parsed = JSON.parse(saved) as WidgetConfig[];
    // Merge with defaults so new widgets are always present
    return DEFAULT_WIDGETS.map((def) => {
      const found = parsed.find((p) => p.id === def.id);
      return found ? { ...def, visible: found.visible } : def;
    });
  } catch {
    return DEFAULT_WIDGETS;
  }
}

function saveWidgets(widgets: WidgetConfig[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(widgets));
}

/* ─── Widget Customization Panel ─── */
function WidgetCustomizer({
  widgets,
  onChange,
  onClose,
}: {
  widgets: WidgetConfig[];
  onChange: (widgets: WidgetConfig[]) => void;
  onClose: () => void;
}) {
  const toggleWidget = (id: WidgetId) => {
    const updated = widgets.map((w) => (w.id === id ? { ...w, visible: !w.visible } : w));
    onChange(updated);
  };

  const resetDefaults = () => {
    onChange(DEFAULT_WIDGETS);
  };

  const visibleCount = widgets.filter((w) => w.visible).length;

  return (
    <div className="absolute right-0 top-full mt-2 z-50 w-72 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl">
      <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Customize Dashboard</h3>
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
          <X className="w-4 h-4 text-slate-400" />
        </button>
      </div>
      <div className="p-2">
        {widgets.map((widget) => (
          <button
            key={widget.id}
            onClick={() => toggleWidget(widget.id)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
          >
            <GripVertical className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
            {widget.visible ? (
              <Eye className="w-4 h-4 text-indigo-500" />
            ) : (
              <EyeOff className="w-4 h-4 text-slate-300 dark:text-slate-600" />
            )}
            <span className={`text-sm flex-1 text-left ${widget.visible ? 'text-slate-700 dark:text-slate-200 font-medium' : 'text-slate-400'}`}>
              {widget.label}
            </span>
            <span className={`w-8 h-5 rounded-full transition-colors flex items-center ${widget.visible ? 'bg-indigo-500 justify-end' : 'bg-slate-200 dark:bg-slate-600 justify-start'}`}>
              <span className="w-3.5 h-3.5 rounded-full bg-white shadow-sm mx-0.5 transition-all" />
            </span>
          </button>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
        <span className="text-xs text-slate-400">{visibleCount}/{widgets.length} visible</span>
        <button
          onClick={resetDefaults}
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 transition-colors"
        >
          <RotateCcw className="w-3 h-3" /> Reset
        </button>
      </div>
    </div>
  );
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
  const { t, locale } = useLocale();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<RecentExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const { readyState } = useWebSocket();
  const [widgets, setWidgets] = useState<WidgetConfig[]>(loadWidgets);
  const [showCustomizer, setShowCustomizer] = useState(false);

  const isVisible = useCallback((id: WidgetId) => widgets.find((w) => w.id === id)?.visible ?? true, [widgets]);

  const handleWidgetsChange = useCallback((updated: WidgetConfig[]) => {
    setWidgets(updated);
    saveWidgets(updated);
  }, []);

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

  // Close customizer when clicking outside
  useEffect(() => {
    if (!showCustomizer) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-customizer]')) setShowCustomizer(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showCustomizer]);

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
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            {t('dashboard.title')}
            <ContextualHelp
              id="dashboard-overview"
              title={locale === 'bg' ? 'Табло' : 'Dashboard'}
              content={locale === 'bg' ? 'Вашият център за управление. Кликнете на карта със статистика за детайли. Персонализирайте уиджети чрез иконата за настройки.' : 'Your command center. Click stat cards for details. Customize widgets with the gear icon.'}
              position="bottom"
            />
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
            {readyState === 'open' ? (
              <><Wifi className="w-3.5 h-3.5 text-emerald-500" /> Live</>
            ) : (
              <><WifiOff className="w-3.5 h-3.5 text-slate-400" /> Offline</>
            )}
          </span>
          <div className="relative" data-customizer>
            <button
              onClick={() => setShowCustomizer(!showCustomizer)}
              className={`p-2 rounded-lg border transition-colors ${
                showCustomizer
                  ? 'border-indigo-300 bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400 dark:border-indigo-800'
                  : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
              }`}
              title="Customize dashboard"
            >
              <Settings2 className="w-4 h-4" />
            </button>
            {showCustomizer && (
              <WidgetCustomizer
                widgets={widgets}
                onChange={handleWidgetsChange}
                onClose={() => setShowCustomizer(false)}
              />
            )}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      {isVisible('stats') && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <StatCard icon={GitBranch} label={t('dashboard.totalWorkflows')} value={stats?.total_workflows ?? 0} color="bg-indigo-500" to="/workflows" />
          <StatCard icon={TrendingUp} label={t('dashboard.activeWorkflows')} value={stats?.active_workflows ?? 0} color="bg-emerald-500" />
          <StatCard icon={Play} label={t('dashboard.totalExecutions')} value={stats?.total_executions ?? 0} color="bg-blue-500" to="/executions" />
          <StatCard icon={Clock} label={t('dashboard.running')} value={stats?.running_executions ?? 0} color="bg-amber-500" />
          <StatCard icon={CheckCircle2} label={t('dashboard.completed')} value={stats?.completed_executions ?? 0} color="bg-emerald-500" />
          <StatCard icon={XCircle} label={t('dashboard.failed')} value={stats?.failed_executions ?? 0} color="bg-red-500" />
        </div>
      )}

      {/* Middle row: Quick Actions + Success Rate + System Health */}
      {(isVisible('quickActions') || isVisible('successRate') || isVisible('systemHealth')) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Quick Actions */}
          {isVisible('quickActions') && (
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
          )}

          {/* Success Rate */}
          {isVisible('successRate') && (
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
          )}

          {/* System Health */}
          {isVisible('systemHealth') && (
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
          )}
        </div>
      )}

      {/* Recent Executions */}
      {isVisible('recentExecutions') && (
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
      )}

      {/* Analytics section */}
      {isVisible('analytics') && (
        <div className="mt-8">
          <AnalyticsDashboard />
        </div>
      )}

      {/* Activity Timeline */}
      {isVisible('activity') && (
        <div className="mt-8 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-4">{t('activity.title')}</h2>
          <ActivityTimeline days={7} limit={20} />
        </div>
      )}
    </div>
  );
}
