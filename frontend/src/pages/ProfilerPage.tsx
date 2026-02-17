import { useState, useEffect, useCallback } from 'react';
import { Cpu, RefreshCw, Trash2, ToggleLeft, ToggleRight, ArrowUpDown, Clock, MemoryStick, AlertTriangle, Zap } from 'lucide-react';
import { profilerApi } from '@/api/profiler';
import { useLocale } from '@/i18n';

interface EndpointStat {
  endpoint: string;
  method: string;
  count: number;
  avg_duration: number;
  max_duration: number;
  avg_memory: number;
  max_memory: number;
  avg_cpu: number;
  error_count: number;
  error_rate: number;
  last_seen: string;
}

interface ProfilerRequest {
  id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  cpu_ms: number;
  memory_kb: number;
  timestamp: string;
}

interface SummaryData {
  enabled: boolean;
  total_requests: number;
  total_errors: number;
  error_rate: number;
  avg_duration_ms: number;
  peak_memory_kb: number;
  endpoints: EndpointStat[];
}

function durationColor(ms: number) {
  if (ms < 100) return 'text-emerald-400';
  if (ms < 500) return 'text-amber-400';
  return 'text-red-400';
}

function durationBg(ms: number) {
  if (ms < 100) return 'bg-emerald-500/20';
  if (ms < 500) return 'bg-amber-500/20';
  return 'bg-red-500/20';
}

function methodBadge(method: string) {
  const colors: Record<string, string> = {
    GET: 'bg-blue-500/20 text-blue-400',
    POST: 'bg-emerald-500/20 text-emerald-400',
    PUT: 'bg-amber-500/20 text-amber-400',
    DELETE: 'bg-red-500/20 text-red-400',
    PATCH: 'bg-purple-500/20 text-purple-400',
  };
  return colors[method] || 'bg-slate-500/20 text-slate-400';
}

export default function ProfilerPage() {
  const { t } = useLocale();
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [requests, setRequests] = useState<ProfilerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'avg_duration' | 'count' | 'avg_memory' | 'error_count'>('avg_duration');
  const [tab, setTab] = useState<'endpoints' | 'requests'>('endpoints');

  const fetchData = useCallback(async () => {
    try {
      const [summaryData, requestsData] = await Promise.all([
        profilerApi.getSummary(),
        profilerApi.getRequests(50),
      ]);
      setSummary(summaryData);
      setRequests(requestsData.requests || []);
    } catch (e) {
      console.error('Profiler fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleToggle = async () => {
    if (!summary) return;
    await profilerApi.setConfig(!summary.enabled);
    fetchData();
  };

  const handleReset = async () => {
    await profilerApi.reset();
    fetchData();
  };

  const sortedEndpoints = summary?.endpoints?.slice().sort((a, b) => {
    return (b[sortBy] as number) - (a[sortBy] as number);
  }) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cpu className="w-7 h-7 text-indigo-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Cloud Profiler</h1>
            <p className="text-sm text-slate-400">CPU, memory & response time profiling</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleToggle}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              summary?.enabled ? 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}>
            {summary?.enabled ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
            {summary?.enabled ? 'Enabled' : 'Disabled'}
          </button>
          <button onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-600/20 text-red-400 hover:bg-red-600/30 transition-colors">
            <Trash2 className="w-4 h-4" /> Reset
          </button>
          <button onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Total Requests</span>
          </div>
          <p className="text-2xl font-bold text-white">{summary?.total_requests?.toLocaleString() || 0}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-amber-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Avg Response</span>
          </div>
          <p className={`text-2xl font-bold ${durationColor(summary?.avg_duration_ms || 0)}`}>
            {summary?.avg_duration_ms || 0} ms
          </p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <MemoryStick className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Peak Memory</span>
          </div>
          <p className="text-2xl font-bold text-purple-400">
            {summary?.peak_memory_kb ? `${(summary.peak_memory_kb / 1024).toFixed(1)} MB` : '0 KB'}
          </p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Error Rate</span>
          </div>
          <p className={`text-2xl font-bold ${(summary?.error_rate || 0) > 5 ? 'text-red-400' : 'text-emerald-400'}`}>
            {summary?.error_rate || 0}%
          </p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-1 bg-slate-800/50 rounded-lg p-1 w-fit">
        <button onClick={() => setTab('endpoints')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === 'endpoints' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
          Endpoints
        </button>
        <button onClick={() => setTab('requests')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === 'requests' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
          Recent Requests
        </button>
      </div>

      {/* Endpoints Table */}
      {tab === 'endpoints' && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-700/50 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Endpoint Performance</h3>
            <div className="flex gap-2">
              {(['avg_duration', 'count', 'avg_memory', 'error_count'] as const).map(key => (
                <button key={key} onClick={() => setSortBy(key)}
                  className={`flex items-center gap-1 px-3 py-1 rounded-md text-xs transition-colors ${sortBy === key ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-500 hover:text-slate-300'}`}>
                  <ArrowUpDown className="w-3 h-3" />
                  {key === 'avg_duration' ? 'Duration' : key === 'count' ? 'Calls' : key === 'avg_memory' ? 'Memory' : 'Errors'}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-xs uppercase tracking-wider border-b border-slate-700/50">
                  <th className="text-left px-5 py-3">Endpoint</th>
                  <th className="text-right px-3 py-3">Calls</th>
                  <th className="text-right px-3 py-3">Avg Duration</th>
                  <th className="text-right px-3 py-3">Max Duration</th>
                  <th className="text-right px-3 py-3">Avg Memory</th>
                  <th className="text-right px-3 py-3">Avg CPU</th>
                  <th className="text-right px-3 py-3">Errors</th>
                </tr>
              </thead>
              <tbody>
                {sortedEndpoints.map((ep, i) => (
                  <tr key={i} className="border-b border-slate-700/30 hover:bg-slate-700/20">
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold mr-2 ${methodBadge(ep.method)}`}>
                        {ep.method}
                      </span>
                      <span className="text-slate-200 font-mono text-xs">{ep.endpoint}</span>
                    </td>
                    <td className="text-right px-3 py-3 text-slate-300">{ep.count}</td>
                    <td className="text-right px-3 py-3">
                      <span className={`px-2 py-0.5 rounded ${durationBg(ep.avg_duration)} ${durationColor(ep.avg_duration)} text-xs font-medium`}>
                        {ep.avg_duration} ms
                      </span>
                    </td>
                    <td className="text-right px-3 py-3">
                      <span className={`${durationColor(ep.max_duration)} text-xs`}>{ep.max_duration} ms</span>
                    </td>
                    <td className="text-right px-3 py-3 text-purple-400 text-xs">{ep.avg_memory} KB</td>
                    <td className="text-right px-3 py-3 text-blue-400 text-xs">{ep.avg_cpu} ms</td>
                    <td className="text-right px-3 py-3">
                      {ep.error_count > 0 ? (
                        <span className="text-red-400 text-xs font-medium">{ep.error_count} ({ep.error_rate}%)</span>
                      ) : (
                        <span className="text-slate-600 text-xs">0</span>
                      )}
                    </td>
                  </tr>
                ))}
                {sortedEndpoints.length === 0 && (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-500">
                      No profiling data yet. Make some API requests to see data here.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Requests */}
      {tab === 'requests' && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-700/50">
            <h3 className="text-sm font-semibold text-white">Recent Requests</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-xs uppercase tracking-wider border-b border-slate-700/50">
                  <th className="text-left px-5 py-3">Time</th>
                  <th className="text-left px-3 py-3">Endpoint</th>
                  <th className="text-right px-3 py-3">Status</th>
                  <th className="text-right px-3 py-3">Duration</th>
                  <th className="text-right px-3 py-3">CPU</th>
                  <th className="text-right px-3 py-3">Memory</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req, i) => (
                  <tr key={i} className="border-b border-slate-700/30 hover:bg-slate-700/20">
                    <td className="px-5 py-2.5 text-slate-500 text-xs font-mono">
                      {new Date(req.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold mr-2 ${methodBadge(req.method)}`}>
                        {req.method}
                      </span>
                      <span className="text-slate-300 font-mono text-xs">{req.path}</span>
                    </td>
                    <td className="text-right px-3 py-2.5">
                      <span className={`text-xs font-medium ${req.status_code < 400 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {req.status_code}
                      </span>
                    </td>
                    <td className="text-right px-3 py-2.5">
                      <span className={`${durationColor(req.duration_ms)} text-xs font-medium`}>{req.duration_ms} ms</span>
                    </td>
                    <td className="text-right px-3 py-2.5 text-blue-400 text-xs">{req.cpu_ms} ms</td>
                    <td className="text-right px-3 py-2.5 text-purple-400 text-xs">{req.memory_kb} KB</td>
                  </tr>
                ))}
                {requests.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500">
                      No requests recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
