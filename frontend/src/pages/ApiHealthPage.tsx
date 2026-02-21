import { useState, useEffect, useCallback } from 'react';
import { Activity, RefreshCw, CheckCircle2, XCircle, AlertTriangle, Clock, Database, Server, Wifi, Cog } from 'lucide-react';
import { apiHealthApi } from '@/api/apiHealth';
import { systemHealthApi, InfrastructureHealth } from '@/api/systemHealth';
import { GitBranch, Container, HardDrive, RefreshCcw } from 'lucide-react';
import { useLocale } from '@/i18n';

interface ServiceStatus {
  service: string;
  status: 'ok' | 'down' | 'degraded';
  response_ms: number;
  error: string | null;
  details?: Record<string, any>;
}

interface HealthData {
  overall: 'healthy' | 'degraded' | 'down';
  timestamp: string;
  services: ServiceStatus[];
}

interface HealthAlert {
  timestamp: string;
  service: string;
  status: string;
  error: string | null;
  response_ms?: number;
}

interface HistoryEntry {
  timestamp: string;
  services: ServiceStatus[];
}

const iconMap: Record<string, any> = {
  'Backend API': Server,
  'PostgreSQL': Database,
  'Redis': Wifi,
  'Celery Workers': Cog,
};

const iconColors: Record<string, string> = {
  'Backend API': 'bg-indigo-500',
  'PostgreSQL': 'bg-blue-500',
  'Redis': 'bg-orange-500',
  'Celery Workers': 'bg-purple-500',
};

const statusDot: Record<string, string> = {
  ok: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  down: 'bg-red-500',
};

const statusBadge: Record<string, string> = {
  ok: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20',
  degraded: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20',
  down: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20',
};

export default function ApiHealthPage() {
  const { t } = useLocale();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [alerts, setAlerts] = useState<HealthAlert[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [infra, setInfra] = useState<InfrastructureHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, alertsRes, historyRes] = await Promise.all([
        apiHealthApi.getStatus(),
        apiHealthApi.getAlerts(),
        apiHealthApi.getHistory(),
      ]);
      setHealth(statusRes);
      setAlerts(alertsRes.alerts || alertsRes || []);
      setHistory(historyRes.history || historyRes || []);
      systemHealthApi.getInfraHealth().then(setInfra).catch(() => {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); const iv = setInterval(fetchData, 30000); return () => clearInterval(iv); }, [fetchData]);

  const timelineData = history.map((entry) => {
    const allOk = entry.services.every((s) => s.status === 'ok');
    const anyDown = entry.services.some((s) => s.status === 'down');
    return { time: entry.timestamp, status: allOk ? 'ok' : anyDown ? 'down' : 'degraded' };
  });

  if (!health) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const diskPct = infra?.disk?.used_pct ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Health</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Real-time service health & infrastructure status</p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Run Check
        </button>
      </div>

      {/* Overall Banner */}
      {health.overall === 'healthy' ? (
        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          <div>
            <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">All Systems Operational</p>
            <p className="text-xs text-emerald-600 dark:text-emerald-400/70">Last checked: {new Date(health.timestamp).toLocaleString()}</p>
          </div>
        </div>
      ) : health.overall === 'degraded' ? (
        <div className="flex items-center gap-3 px-4 py-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <div>
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">Degraded Performance</p>
            <p className="text-xs text-amber-600 dark:text-amber-400/70">Last checked: {new Date(health.timestamp).toLocaleString()}</p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl">
          <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-800 dark:text-red-300">System Outage</p>
            <p className="text-xs text-red-600 dark:text-red-400/70">Last checked: {new Date(health.timestamp).toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* Service Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {health.services.map((svc) => {
          const Icon = iconMap[svc.service] || Server;
          const color = iconColors[svc.service] || 'bg-slate-500';
          return (
            <div key={svc.service} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center`}>
                  <Icon className="w-4.5 h-4.5 text-white" />
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadge[svc.status] || statusBadge.down}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${statusDot[svc.status] || 'bg-red-500'}`} />
                  {svc.status === 'ok' ? 'OK' : svc.status.toUpperCase()}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{svc.service}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{svc.response_ms.toFixed(0)} ms response</p>
              {svc.details && Object.entries(svc.details).map(([k, v]) => (
                <p key={k} className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                  {k}: <span className="text-slate-600 dark:text-slate-300">{String(v)}</span>
                </p>
              ))}
              {svc.error && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 rounded-lg px-2 py-1">{svc.error}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Health Timeline */}
      {timelineData.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Health Timeline</h3>
            </div>
            <span className="text-xs text-slate-400">last {timelineData.length} checks</span>
          </div>
          <div className="flex gap-0.5 items-end h-8">
            {timelineData.map((entry, i) => (
              <div
                key={i}
                className={`flex-1 rounded-sm ${statusDot[entry.status]} opacity-70 hover:opacity-100 transition-opacity cursor-pointer`}
                style={{ height: '100%' }}
                title={`${new Date(entry.time).toLocaleTimeString()} — ${entry.status}`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1.5">
            <span className="text-[10px] text-slate-400">{timelineData.length > 0 ? new Date(timelineData[0].time).toLocaleTimeString() : ''}</span>
            <span className="text-[10px] text-slate-400">{timelineData.length > 0 ? new Date(timelineData[timelineData.length - 1].time).toLocaleTimeString() : ''}</span>
          </div>
        </div>
      )}

      {/* Infrastructure & Sync */}
      {infra && (
        <>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-500" />
            Infrastructure & Sync
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Auto-Sync */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-500 flex items-center justify-center">
                  <RefreshCcw className="w-4.5 h-4.5 text-white" />
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${infra.auto_sync.status === 'ok' ? statusBadge.ok : statusBadge.down}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${infra.auto_sync.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  {infra.auto_sync.state}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Auto-Sync</p>
              {infra.auto_sync.pid > 0 && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">PID {infra.auto_sync.pid}</p>}
              {infra.auto_sync.error && <p className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 rounded-lg px-2 py-1">{infra.auto_sync.error}</p>}
            </div>

            {/* GitHub */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-500 flex items-center justify-center">
                  <GitBranch className="w-4.5 h-4.5 text-white" />
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${infra.github.status === 'ok' ? statusBadge.ok : statusBadge.down}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${infra.github.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  {infra.github.status === 'ok' ? 'OK' : 'DOWN'}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">GitHub</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{infra.github.response_ms} ms</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 truncate" title={infra.github.last_message}>
                <code className="text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-1 py-0.5 rounded text-[10px]">{infra.github.last_commit}</code>
                <span className="ml-1">{infra.github.last_message}</span>
              </p>
              <p className="text-[10px] text-slate-400 mt-0.5">{infra.github.last_commit_time}</p>
            </div>

            {/* Docker */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-blue-500 flex items-center justify-center">
                  <Server className="w-4.5 h-4.5 text-white" />
                </div>
                <span className={`text-sm font-bold ${infra.docker.all_healthy ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>{infra.docker.total}/{infra.docker.total}</span>
              </div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Docker Containers</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {infra.docker.containers.slice(0, 6).map((ct) => (
                  <span key={ct.name} className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${ct.state === 'running' ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400' : 'bg-red-50 border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-400'}`}>
                    <span className={`w-1 h-1 rounded-full ${ct.state === 'running' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    {ct.name.replace('rpa-', '')}
                  </span>
                ))}
                {infra.docker.containers.length > 6 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 font-medium border border-slate-200 dark:border-slate-600">
                    +{infra.docker.containers.length - 6} more
                  </span>
                )}
              </div>
            </div>

            {/* Disk */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-purple-500 flex items-center justify-center">
                  <HardDrive className="w-4.5 h-4.5 text-white" />
                </div>
                <span className={`text-sm font-bold ${diskPct > 85 ? 'text-red-600 dark:text-red-400' : diskPct > 60 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>{diskPct.toFixed(1)}%</span>
              </div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Disk Space</p>
              <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2 mt-2">
                <div className={`h-full rounded-full transition-all ${diskPct > 85 ? 'bg-red-500' : diskPct > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${diskPct}%` }} />
              </div>
              <div className="flex justify-between mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                <span>{infra.disk.used_gb.toFixed(1)} GB used</span>
                <span>{infra.disk.free_gb.toFixed(0)} GB free</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Alerts */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Recent Alerts</h3>
          </div>
          <span className="text-xs text-slate-400">{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
        </div>
        {alerts.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-200 dark:text-emerald-500/20 mx-auto mb-2" />
            <p className="text-sm text-slate-400">No alerts — all services have been healthy.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700 max-h-72 overflow-y-auto">
            {alerts.map((alert, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${alert.status === 'down' ? 'bg-red-500' : alert.status === 'degraded' ? 'bg-amber-500' : 'bg-slate-300'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-white">{alert.service}</span>
                    <span className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded-full border ${statusBadge[alert.status] || statusBadge.down}`}>{alert.status}</span>
                  </div>
                  {alert.error && <p className="text-xs text-slate-500 truncate mt-0.5">{alert.error}</p>}
                </div>
                <span className="text-xs text-slate-400 flex-shrink-0">{new Date(alert.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
