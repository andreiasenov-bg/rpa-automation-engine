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

function serviceIcon(name: string) {
  switch (name) {
    case 'Backend API': return Server;
    case 'PostgreSQL': return Database;
    case 'Redis': return Wifi;
    case 'Celery Workers': return Cog;
    default: return Server;
  }
}

function statusColor(status: string) {
  if (status === 'ok') return { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400', glow: 'hover:shadow-emerald-500/20' };
  if (status === 'degraded') return { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400', glow: 'hover:shadow-amber-500/20' };
  return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-400', glow: 'hover:shadow-red-500/20' };
}

function overallBanner(overall: string) {
  if (overall === 'healthy') return { bg: 'bg-gradient-to-r from-emerald-900/40 via-emerald-800/20 to-emerald-900/40', border: 'border-emerald-500/20', text: 'text-emerald-400', label: 'All Systems Operational', Icon: CheckCircle2 };
  if (overall === 'degraded') return { bg: 'bg-gradient-to-r from-amber-900/40 via-amber-800/20 to-amber-900/40', border: 'border-amber-500/20', text: 'text-amber-400', label: 'Degraded Performance', Icon: AlertTriangle };
  return { bg: 'bg-gradient-to-r from-red-900/40 via-red-800/20 to-red-900/40', border: 'border-red-500/20', text: 'text-red-400', label: 'System Outage', Icon: XCircle };
}

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
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading health data...</p>
        </div>
      </div>
    );
  }

  const banner = overallBanner(health.overall);
  const BannerIcon = banner.Icon;
  const diskPct = infra?.disk?.used_pct ?? 0;
  const diskBarColor = diskPct > 85 ? 'from-red-500 to-red-400' : diskPct > 60 ? 'from-amber-500 to-amber-400' : 'from-emerald-500 via-emerald-400 to-teal-400';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
              <Activity className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">API Health Monitor</h1>
              <p className="text-sm text-slate-500">Real-time service health & diagnostics</p>
            </div>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Run Health Check
        </button>
      </div>

      {/* Overall Status Banner */}
      <div className={`${banner.bg} border ${banner.border} rounded-2xl p-5 backdrop-blur-sm transition-all duration-500`}>
        <div className="flex items-center gap-4">
          <div className={`p-2 rounded-full ${banner.text} bg-current/10`}>
            <BannerIcon className="w-6 h-6" />
          </div>
          <div>
            <h2 className={`text-lg font-bold ${banner.text}`}>{banner.label}</h2>
            <p className="text-sm text-slate-500">Last checked: {new Date(health.timestamp).toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {health.services.map((svc) => {
          const c = statusColor(svc.status);
          const Icon = serviceIcon(svc.service);
          return (
            <div key={svc.service} className={`group relative ${c.bg} border ${c.border} rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-xl ${c.glow} cursor-default overflow-hidden`}>
              {/* Subtle gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent rounded-2xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <Icon className={`w-6 h-6 ${c.text} opacity-80`} />
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${c.dot} shadow-lg animate-pulse`} />
                    <span className={`text-xs font-bold uppercase tracking-widest ${c.text}`}>
                      {svc.status === 'ok' ? 'OK' : svc.status.toUpperCase()}
                    </span>
                  </div>
                </div>
                <h3 className="text-white font-semibold text-sm mb-1">{svc.service}</h3>
                <div className="flex items-baseline gap-1 mb-2">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span className="text-xs text-slate-400">{svc.response_ms.toFixed(0)} ms</span>
                </div>
                {svc.details && Object.entries(svc.details).map(([k, v]) => (
                  <p key={k} className="text-[11px] text-slate-500 leading-relaxed">
                    <span className="text-slate-400">{k}:</span>{' '}
                    <span className="font-medium text-slate-300">{String(v)}</span>
                  </p>
                ))}
                {svc.error && (
                  <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded-lg px-2.5 py-1.5 border border-red-500/20">{svc.error}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Health Timeline */}
      {timelineData.length > 0 && (
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-4 h-4 text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-300 tracking-wide uppercase">Health Timeline</h3>
            <span className="text-xs text-slate-600 ml-auto">last {timelineData.length} checks</span>
          </div>
          <div className="flex gap-1 items-end">
            {timelineData.map((entry, i) => {
              const c = statusColor(entry.status);
              return (
                <div
                  key={i}
                  className={`flex-1 min-w-[6px] h-10 rounded-full ${c.dot} transition-all duration-300 hover:h-14 hover:opacity-100 opacity-80 cursor-pointer group relative`}
                  title={`${new Date(entry.time).toLocaleTimeString()} — ${entry.status}`}
                >
                  <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-[10px] text-slate-300 opacity-0 group-hover:opacity-100 transition-all duration-200 whitespace-nowrap pointer-events-none z-10 shadow-xl">
                    {new Date(entry.time).toLocaleTimeString()}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-[10px] text-slate-600">{timelineData.length > 0 ? new Date(timelineData[0].time).toLocaleTimeString() : ''}</span>
            <span className="text-[10px] text-slate-600">{timelineData.length > 0 ? new Date(timelineData[timelineData.length - 1].time).toLocaleTimeString() : ''}</span>
          </div>
        </div>
      )}

      {/* Gradient Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />

      {/* Infrastructure & Sync */}
      {infra && (
        <div>
          <div className="flex items-center gap-3 mb-5">
            <div className="p-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
              <Container className="w-4 h-4 text-indigo-400" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">Infrastructure & Sync</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Auto-Sync */}
            <div className="group relative bg-slate-800/40 border border-slate-700/40 rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-xl hover:shadow-indigo-500/10 hover:border-indigo-500/30 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.03] to-transparent rounded-2xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <RefreshCcw className="w-5 h-5 text-indigo-400 group-hover:rotate-180 transition-transform duration-700" />
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${infra.auto_sync.status === 'ok' ? 'bg-emerald-400 shadow-emerald-400/50' : 'bg-red-400 shadow-red-400/50'} shadow-lg animate-pulse`} />
                    <span className={`text-xs font-bold uppercase tracking-widest ${infra.auto_sync.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>{infra.auto_sync.state}</span>
                  </div>
                </div>
                <h3 className="text-white font-semibold text-sm mb-1">Auto-Sync</h3>
                {infra.auto_sync.pid > 0 && <p className="text-xs text-slate-500">PID <span className="text-slate-300 font-mono">{infra.auto_sync.pid}</span></p>}
                {infra.auto_sync.error && <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded-lg px-2.5 py-1.5 border border-red-500/20">{infra.auto_sync.error}</p>}
              </div>
            </div>

            {/* GitHub */}
            <div className="group relative bg-slate-800/40 border border-slate-700/40 rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-xl hover:shadow-emerald-500/10 hover:border-emerald-500/30 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/[0.03] to-transparent rounded-2xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <GitBranch className="w-5 h-5 text-emerald-400" />
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${infra.github.status === 'ok' ? 'bg-emerald-400 shadow-emerald-400/50' : 'bg-red-400 shadow-red-400/50'} shadow-lg animate-pulse`} />
                    <span className={`text-xs font-bold uppercase tracking-widest ${infra.github.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>{infra.github.status === 'ok' ? 'OK' : 'DOWN'}</span>
                  </div>
                </div>
                <h3 className="text-white font-semibold text-sm mb-2">GitHub</h3>
                <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                  <Clock className="w-3 h-3" />
                  <span>{infra.github.response_ms} ms</span>
                </div>
                <p className="text-xs text-slate-500 truncate" title={infra.github.last_message}>
                  <code className="text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded font-mono text-[10px]">{infra.github.last_commit}</code>
                  <span className="ml-1.5">{infra.github.last_message}</span>
                </p>
                <p className="text-[10px] text-slate-600 mt-1">{infra.github.last_commit_time}</p>
              </div>
            </div>

            {/* Docker Containers */}
            <div className="group relative bg-slate-800/40 border border-slate-700/40 rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-xl hover:shadow-blue-500/10 hover:border-blue-500/30 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/[0.03] to-transparent rounded-2xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <Server className="w-5 h-5 text-blue-400" />
                  <span className={`text-sm font-bold ${infra.docker.all_healthy ? 'text-emerald-400' : 'text-amber-400'}`}>{infra.docker.total}/{infra.docker.total}</span>
                </div>
                <h3 className="text-white font-semibold text-sm mb-3">Docker Containers</h3>
                <div className="flex flex-wrap gap-1.5">
                  {infra.docker.containers.slice(0, 6).map((ct) => (
                    <span key={ct.name} className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${ct.state === 'running' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : 'bg-red-500/10 border-red-500/20 text-red-300'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${ct.state === 'running' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                      {ct.name.replace('rpa-', '')}
                    </span>
                  ))}
                  {infra.docker.containers.length > 6 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/50 border border-slate-600/50 text-slate-400 font-medium">
                      +{infra.docker.containers.length - 6} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Disk Space */}
            <div className="group relative bg-slate-800/40 border border-slate-700/40 rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-xl hover:shadow-purple-500/10 hover:border-purple-500/30 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/[0.03] to-transparent rounded-2xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <HardDrive className="w-5 h-5 text-purple-400" />
                  <span className={`text-sm font-bold ${diskPct > 85 ? 'text-red-400' : diskPct > 60 ? 'text-amber-400' : 'text-emerald-400'}`}>{diskPct.toFixed(1)}%</span>
                </div>
                <h3 className="text-white font-semibold text-sm mb-3">Disk Space</h3>
                <div className="w-full bg-slate-700/50 rounded-full h-2.5 overflow-hidden mb-2">
                  <div className={`h-full bg-gradient-to-r ${diskBarColor} rounded-full transition-all duration-1000 ease-out`} style={{ width: `${diskPct}%` }} />
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">{infra.disk.used_gb.toFixed(1)} GB used</span>
                  <span className="text-slate-500">{infra.disk.free_gb.toFixed(0)} GB free</span>
                </div>
                <p className="text-[10px] text-slate-600 mt-1">Total: {infra.disk.total_gb.toFixed(1)} GB</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Gradient Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />

      {/* Alerts */}
      <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl backdrop-blur-sm overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-700/30">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white tracking-wide">Recent Alerts</h3>
          <span className="text-xs text-slate-600 ml-auto font-medium">{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
        </div>
        {alerts.length === 0 ? (
          <div className="px-6 py-10 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/30 mx-auto mb-2" />
            <p className="text-slate-500 text-sm">No alerts — all services have been healthy.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/20 max-h-72 overflow-y-auto">
            {alerts.map((alert, i) => (
              <div key={i} className="px-6 py-3.5 flex items-center gap-4 hover:bg-slate-700/10 transition-colors duration-200">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${alert.status === 'down' ? 'bg-red-400' : alert.status === 'degraded' ? 'bg-amber-400' : 'bg-slate-400'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{alert.service}</span>
                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${alert.status === 'down' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>{alert.status}</span>
                  </div>
                  {alert.error && <p className="text-xs text-slate-500 truncate mt-0.5">{alert.error}</p>}
                </div>
                <span className="text-xs text-slate-600 flex-shrink-0 font-mono">{new Date(alert.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
