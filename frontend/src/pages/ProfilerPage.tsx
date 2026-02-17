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

type SortField = 'duration' | 'calls' | 'memory' | 'errors';

export default function ProfilerPage() {
  const { t } = useLocale();
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [requests, setRequests] = useState<ProfilerRequest[]>([]);
  const [enabled, setEnabled] = useState(true);
  const [activeTab, setActiveTab] = useState<'endpoints' | 'requests'>('endpoints');
  const [sortBy, setSortBy] = useState<SortField>('duration');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [summaryRes, configRes] = await Promise.all([
        profilerApi.getSummary(),
        profilerApi.getConfig(),
      ]);
      setSummary(summaryRes.data);
      setEnabled(configRes.data.enabled);
      if (activeTab === 'requests') {
        const reqRes = await profilerApi.getRequests(1, 50);
        setRequests(reqRes.data.items || reqRes.data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load profiler data');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleToggle = async () => {
    try {
      await profilerApi.setConfig({ enabled: !enabled });
      setEnabled(!enabled);
    } catch (err) {
      console.error('Failed to toggle profiler', err);
    }
  };

  const handleReset = async () => {
    try {
      await profilerApi.reset();
      await fetchData();
    } catch (err) {
      console.error('Failed to reset profiler', err);
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1) return `${(ms * 1000).toFixed(0)} µs`;
    if (ms < 1000) return `${ms.toFixed(1)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
  };

  const formatMemory = (kb: number) => {
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  const getDurationColor = (ms: number) => {
    if (ms < 100) return 'text-emerald-600';
    if (ms < 500) return 'text-amber-600';
    return 'text-red-600';
  };

  const getStatusColor = (code: number) => {
    if (code < 300) return 'text-emerald-600';
    if (code < 400) return 'text-amber-600';
    return 'text-red-600';
  };

  const sortedEndpoints = summary?.endpoints?.slice().sort((a, b) => {
    switch (sortBy) {
      case 'duration': return b.avg_duration - a.avg_duration;
      case 'calls': return b.count - a.count;
      case 'memory': return b.avg_memory - a.avg_memory;
      case 'errors': return b.error_count - a.error_count;
      default: return 0;
    }
  }) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <a href="/" className="hover:text-slate-700">🏠</a>
        <span>/</span>
        <span className="text-slate-700 font-medium">Profiler</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
            <Cpu className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Cloud Profiler</h1>
            <p className="text-sm text-slate-500">CPU, memory & response time profiling</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggle}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              enabled
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                : 'bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200'
            }`}
          >
            {enabled ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
            {enabled ? 'Enabled' : 'Disabled'}
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={() => { setLoading(true); fetchData(); }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <Zap className="w-4 h-4 text-indigo-500" />
            TOTAL REQUESTS
          </div>
          <div className="text-3xl font-bold text-slate-800">{summary?.total_requests || 0}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <Clock className="w-4 h-4 text-amber-500" />
            AVG RESPONSE
          </div>
          <div className={`text-3xl font-bold ${getDurationColor(summary?.avg_duration_ms || 0)}`}>
            {formatDuration(summary?.avg_duration_ms || 0)}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <MemoryStick className="w-4 h-4 text-violet-500" />
            PEAK MEMORY
          </div>
          <div className="text-3xl font-bold text-slate-800">{formatMemory(summary?.peak_memory_kb || 0)}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            ERROR RATE
          </div>
          <div className={`text-3xl font-bold ${(summary?.error_rate || 0) > 10 ? 'text-red-600' : (summary?.error_rate || 0) > 5 ? 'text-amber-600' : 'text-emerald-600'}`}>
            {(summary?.error_rate || 0).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab('endpoints')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'endpoints'
              ? 'bg-white text-slate-800 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Endpoints
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'requests'
              ? 'bg-white text-slate-800 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Recent Requests
        </button>
      </div>

      {/* Endpoints Table */}
      {activeTab === 'endpoints' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Endpoint Performance</h3>
            <div className="flex gap-1">
              {(['duration', 'calls', 'memory', 'errors'] as SortField[]).map((field) => (
                <button
                  key={field}
                  onClick={() => setSortBy(field)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    sortBy === field
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <ArrowUpDown className="w-3 h-3" />
                  {field.charAt(0).toUpperCase() + field.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Endpoint</th>
                <th className="text-center px-3 py-3 font-medium">Calls</th>
                <th className="text-right px-3 py-3 font-medium">Avg Duration</th>
                <th className="text-right px-3 py-3 font-medium">Max Duration</th>
                <th className="text-right px-3 py-3 font-medium">Avg Memory</th>
                <th className="text-right px-3 py-3 font-medium">Avg CPU</th>
                <th className="text-center px-5 py-3 font-medium">Errors</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedEndpoints.map((ep, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        ep.method === 'GET' ? 'bg-blue-50 text-blue-600' :
                        ep.method === 'POST' ? 'bg-green-50 text-green-600' :
                        ep.method === 'PUT' ? 'bg-amber-50 text-amber-600' :
                        ep.method === 'DELETE' ? 'bg-red-50 text-red-600' :
                        'bg-slate-50 text-slate-600'
                      }`}>
                        {ep.method}
                      </span>
                      <span className="text-sm text-slate-700 font-mono">{ep.endpoint}</span>
                    </div>
                  </td>
                  <td className="text-center px-3 py-3 text-sm text-slate-600">{ep.count}</td>
                  <td className={`text-right px-3 py-3 text-sm font-medium ${getDurationColor(ep.avg_duration)}`}>
                    {formatDuration(ep.avg_duration)}
                  </td>
                  <td className={`text-right px-3 py-3 text-sm ${getDurationColor(ep.max_duration)}`}>
                    {formatDuration(ep.max_duration)}
                  </td>
                  <td className="text-right px-3 py-3 text-sm text-slate-600">
                    {formatMemory(ep.avg_memory)}
                  </td>
                  <td className="text-right px-3 py-3 text-sm text-slate-600">
                    {ep.avg_cpu > 0 ? `${ep.avg_cpu.toFixed(1)} ms` : '—'}
                  </td>
                  <td className="text-center px-5 py-3">
                    {ep.error_count > 0 ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600">
                        {ep.error_count}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-300">0</span>
                    )}
                  </td>
                </tr>
              ))}
              {sortedEndpoints.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    No profiling data yet. Make some API calls to see results.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Recent Requests Table */}
      {activeTab === 'requests' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Recent Requests</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Endpoint</th>
                <th className="text-center px-3 py-3 font-medium">Status</th>
                <th className="text-right px-3 py-3 font-medium">Duration</th>
                <th className="text-right px-3 py-3 font-medium">CPU</th>
                <th className="text-right px-3 py-3 font-medium">Memory</th>
                <th className="text-right px-5 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {requests.map((req, i) => (
                <tr key={req.id || i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        req.method === 'GET' ? 'bg-blue-50 text-blue-600' :
                        req.method === 'POST' ? 'bg-green-50 text-green-600' :
                        req.method === 'PUT' ? 'bg-amber-50 text-amber-600' :
                        req.method === 'DELETE' ? 'bg-red-50 text-red-600' :
                        'bg-slate-50 text-slate-600'
                      }`}>
                        {req.method}
                      </span>
                      <span className="text-sm text-slate-700 font-mono">{req.path}</span>
                    </div>
                  </td>
                  <td className="text-center px-3 py-3">
                    <span className={`text-sm font-medium ${getStatusColor(req.status_code)}`}>
                      {req.status_code}
                    </span>
                  </td>
                  <td className={`text-right px-3 py-3 text-sm font-medium ${getDurationColor(req.duration_ms)}`}>
                    {formatDuration(req.duration_ms)}
                  </td>
                  <td className="text-right px-3 py-3 text-sm text-slate-600">
                    {req.cpu_ms > 0 ? `${req.cpu_ms.toFixed(1)} ms` : '—'}
                  </td>
                  <td className="text-right px-3 py-3 text-sm text-slate-600">
                    {formatMemory(req.memory_kb)}
                  </td>
                  <td className="text-right px-5 py-3 text-sm text-slate-400">
                    {new Date(req.timestamp).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {requests.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No recent requests recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
