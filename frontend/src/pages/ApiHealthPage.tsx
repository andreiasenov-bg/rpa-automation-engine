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
  if (status === 'ok') return { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' };
  if (status === 'degraded') return { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400' };
  return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-400' };
}

function overallBanner(overall: string) {
  if (overall === 'healthy') return { bg: 'bg-emerald-600/20', text: 'text-emerald-400', label: 'All Systems Operational', Icon: CheckCircle2 };
  if (overall === 'degraded') return { bg: 'bg-amber-600/20', text: 'text-amber-400', label: 'Degraded Performance', Icon: AlertTriangle };
  return { bg: 'bg-red-600/20', text: 'text-red-400', label: 'System Outage', Icon: XCircle };
}

export default function ApiHealthPage() {
  const { t } = useLocale();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [alerts, setAlerts] = useState<HealthAlert[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [infra, setInfra] = useState<InfrastructureHealth | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statusData, alertsData, historyData] = await Promise.all([
        apiHealthApi.getStatus(),
        apiHealthApi.getAlerts(),
        apiHealthApi.getHistory(120),
      ]);
      setHealth(statusData);
      systemHealthApi.getInfraHealth().then(setInfra).catch(() => {});
      setAlerts(alertsData.alerts || []);
      setHistory(historyData.history || []);
    } catch (e) {
      console.error('Health fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleManualCheck = async () => {
    setChecking(true);
    try {
      const result = await apiHealthApi.triggerCheck();
      setHealth(result);
      // Refresh alerts and history too
      const [alertsData, historyData] = await Promise.all([
        apiHealthApi.getAlerts(),
        apiHealthApi.getHistory(120),
      ]);
      setAlerts(alertsData.alerts || []);
      setHistory(historyData.history || []);
    } catch (e) {
      console.error('Manual check error:', e);
    } finally {
      setChecking(false);
    }
  };

  // Build mini timeline from history (last 60 entries)
  const timelineData = history.slice(0, 60).reverse().map(entry => {
    const allOk = entry.services.every(s => s.status === 'ok');
    const anyDown = entry.services.some(s => s.status === 'down');
    return { time: entry.timestamp, status: allOk ? 'ok' : anyDown ? 'down' : 'degraded' };
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const banner = health ? overallBanner(health.overall) : overallBanner('down');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-7 h-7 text-indigo-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">API Health Monitor</h1>
            <p className="text-sm text-slate-400">Real-time service health & diagnostics</p>
          </div>
        </div>
        <button onClick={handleManualCheck} disabled={checking}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors">
          <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
          Run Health Check
        </button>
      </div>

      {/* Overall Status Banner */}
      <div className={`${banner.bg} border ${banner.text === 'text-emerald-400' ? 'border-emerald-500/30' : banner.text === 'text-amber-400' ? 'border-amber-500/30' : 'border-red-500/30'} rounded-xl px-6 py-4 flex items-center gap-4`}>
        <banner.Icon className={`w-6 h-6 ${banner.text}`} />
        <div>
          <p className={`text-lg font-semibold ${banner.text}`}>{banner.label}</p>
          <p className="text-sm text-slate-400">
            Last checked: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'Never'}
          </p>
        </div>
      </div>

      {/* Service Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {health?.services.map((svc, i) => {
          const colors = statusColor(svc.status);
          const SvcIcon = serviceIcon(svc.service);
          return (
            <div key={i} className={`${colors.bg} border ${colors.border} rounded-xl p-5 transition-all`}>
              <div className="flex items-center justify-between mb-3">
                <SvcIcon className={`w-5 h-5 ${colors.text}`} />
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${colors.dot} ${svc.status === 'ok' ? '' : 'animate-pulse'}`} />
                  <span className={`text-xs font-semibold uppercase ${colors.text}`}>{svc.status}</span>
                </div>
              </div>
              <h3 className="text-white font-semibold text-sm mb-1">{svc.service}</h3>
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <Clock className="w-3 h-3" />
                <span>{svc.response_ms} ms</span>
              </div>
              {svc.error && (
                <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1 break-all">
                  {svc.error.substring(0, 120)}
                </p>
              )}
              {svc.details && Object.keys(svc.details).length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {Object.entries(svc.details).map(([k, v]) => (
                    <p key={k} className="text-[11px] text-slate-500">
                      <span className="text-slate-400">{k}:</span> {String(v)}
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Health Timeline */}
      {timelineData.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Health Timeline (last {timelineData.length} checks)</h3>
          <div className="flex gap-0.5 items-end h-8">
            {timelineData.map((entry, i) => (
              <div key={i}
                className={`flex-1 rounded-sm min-w-[3px] h-full ${
                  entry.status === 'ok' ? 'bg-emerald-500/60' : entry.status === 'degraded' ? 'bg-amber-500/60' : 'bg-red-500/60'
                }`}
                title={`${new Date(entry.time).toLocaleTimeString()} — ${entry.status}`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-slate-600">
              {timelineData.length > 0 ? new Date(timelineData[0].time).toLocaleTimeString() : ''}
            </span>
            <span className="text-[10px] text-slate-600">
              {timelineData.length > 0 ? new Date(timelineData[timelineData.length - 1].time).toLocaleTimeString() : ''}
            </span>
          </div>
        </div>
      )}


      {/* Infrastructure & Sync */}
      {infra && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Container className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Infrastructure & Sync</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Auto-Sync */}
            <div className={`${infra.auto_sync.status === 'ok' ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'} border rounded-xl p-5`}>
              <div className="flex items-center justify-between mb-3">
                <RefreshCcw className={`w-5 h-5 ${infra.auto_sync.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`} />
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${infra.auto_sync.status === 'ok' ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'}`} />
                  <span className={`text-xs font-semibold uppercase ${infra.auto_sync.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>{infra.auto_sync.state}</span>
                </div>
              </div>
              <h3 className="text-white font-semibold text-sm mb-1">Auto-Sync</h3>
              {infra.auto_sync.pid > 0 && <p className="text-xs text-slate-400">PID {infra.auto_sync.pid}</p>}
              {infra.auto_sync.error && <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{infra.auto_sync.error}</p>}
            </div>

            {/* GitHub */}
            <div className={`${infra.github.status === 'ok' ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'} border rounded-xl p-5`}>
              <div className="flex items-center justify-between mb-3">
                <GitBranch className={`w-5 h-5 ${infra.github.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`} />
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${infra.github.status === 'ok' ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'}`} />
                  <span className={`text-xs font-semibold uppercase ${infra.github.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>{infra.github.status}</span>
                </div>
              </div>
              <h3 className="text-white font-semibold text-sm mb-1">GitHub</h3>
              <div className="flex items-center gap-1 text-xs text-slate-400"><Clock className="w-3 h-3" /><span>{infra.github.response_ms} ms</span></div>
              <p className="text-xs text-slate-500 mt-1 truncate" title={infra.github.last_message}><code className="text-indigo-300">{infra.github.last_commit}</code> {infra.github.last_message}</p>
              <p className="text-[10px] text-slate-600 mt-0.5">{infra.github.last_commit_time}</p>
            </div>

            {/* Docker Containers */}
            <div className={`${infra.docker.status === 'ok' ? 'bg-emerald-500/10 border-emerald-500/30' : infra.docker.status === 'degraded' ? 'bg-amber-500/10 border-amber-500/30' : 'bg-red-500/10 border-red-500/30'} border rounded-xl p-5`}>
              <div className="flex items-center justify-between mb-3">
                <Server className={`w-5 h-5 ${infra.docker.status === 'ok' ? 'text-emerald-400' : infra.docker.status === 'degraded' ? 'text-amber-400' : 'text-red-400'}`} />
                <span className={`text-xs font-semibold ${infra.docker.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>{infra.docker.containers.filter(c => c.state === 'running').length}/{infra.docker.total}</span>
              </div>
              <h3 className="text-white font-semibold text-sm mb-2">Docker Containers</h3>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {infra.docker.containers.map((c, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className={`w-1.5 h-1.5 rounded-full ${c.state === 'running' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                    <span className="text-slate-400 truncate flex-1" title={c.name}>{c.name.replace('rpa-', '')}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Disk Space */}
            <div className={`${infra.disk.status === 'ok' ? 'bg-emerald-500/10 border-emerald-500/30' : infra.disk.status === 'degraded' ? 'bg-amber-500/10 border-amber-500/30' : 'bg-red-500/10 border-red-500/30'} border rounded-xl p-5`}>
              <div className="flex items-center justify-between mb-3">
                <HardDrive className={`w-5 h-5 ${infra.disk.status === 'ok' ? 'text-emerald-400' : infra.disk.status === 'degraded' ? 'text-amber-400' : 'text-red-400'}`} />
                <span className={`text-xs font-semibold ${infra.disk.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>{infra.disk.used_pct}%</span>
              </div>
              <h3 className="text-white font-semibold text-sm mb-2">Disk Space</h3>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden mb-2">
                <div className={`h-full rounded-full transition-all ${infra.disk.used_pct < 85 ? 'bg-emerald-400' : infra.disk.used_pct < 95 ? 'bg-amber-400' : 'bg-red-400'}`} style={{ width: infra.disk.used_pct + '%' }} />
              </div>
              <div className="flex justify-between text-xs text-slate-400">
                <span>{infra.disk.used_gb} GB used</span>
                <span>{infra.disk.free_gb} GB free</span>
              </div>
              <p className="text-[10px] text-slate-600 mt-1">Total: {infra.disk.total_gb} GB</p>
            </div>
          </div>
        </div>
      )}

      {/* Alerts */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-700/50 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white">Recent Alerts</h3>
          <span className="text-xs text-slate-500 ml-auto">{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
        </div>
        {alerts.length === 0 ? (
          <div className="px-5 py-8 text-center text-slate-500 text-sm">
            No alerts — all services have been healthy.
          </div>
        ) : (
          <div className="divide-y divide-slate-700/30 max-h-64 overflow-y-auto">
            {alerts.map((alert, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-4">
                <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{alert.service}</span>
                    <span className="text-xs text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">{alert.status}</span>
                  </div>
                  {alert.error && <p className="text-xs text-slate-400 truncate">{alert.error}</p>}
                </div>
                <span className="text-xs text-slate-500 flex-shrink-0">
                  {new Date(alert.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
