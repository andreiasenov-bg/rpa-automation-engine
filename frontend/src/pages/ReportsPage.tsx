/**
 * ReportsPage — Full analytics & reporting hub.
 *
 * Sections:
 *  1. Daily trend chart (area + bar stacked)
 *  2. KPI summary cards
 *  3. Workflow heatmap table
 *  4. Looker Studio embedded report
 *  5. Data export panel (CSV / Google Sheets sync)
 */

import { useEffect, useState, useMemo, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, ComposedChart,
} from 'recharts';
import {
  BarChart3, TrendingUp, Download, RefreshCw,
  CheckCircle2, XCircle, Clock, Activity, Loader2,
  ExternalLink, FileSpreadsheet, Link2, ArrowUpRight,
  ArrowDownRight, Minus, Calendar, Table2, PieChart as PieIcon,
  Settings2,
} from 'lucide-react';
import {
  fetchExecutionOverview, fetchExecutionTimeline, fetchWorkflowPerformance,
  type ExecutionOverview, type ExecutionTimeline, type WorkflowPerformanceEntry,
} from '@/api/analytics';
import {
  fetchDailySummary, syncToGoogleSheets,
  type SummaryRow,
} from '@/api/reports';
import client from '@/api/client';

/* ─── Colors ─── */
const C = {
  indigo: '#6366f1',
  emerald: '#10b981',
  red: '#ef4444',
  amber: '#f59e0b',
  blue: '#3b82f6',
  violet: '#8b5cf6',
  slate: '#94a3b8',
};

/* ─── Period Selector ─── */
function PeriodSelector({ value, onChange }: { value: number; onChange: (d: number) => void }) {
  const opts = [
    { label: '7d', days: 7 },
    { label: '30d', days: 30 },
    { label: '90d', days: 90 },
  ];
  return (
    <div className="flex gap-1 bg-slate-100 dark:bg-slate-700 rounded-lg p-1">
      {opts.map(({ label, days }) => (
        <button key={days} onClick={() => onChange(days)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
            value === days
              ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}>{label}</button>
      ))}
    </div>
  );
}

/* ─── KPI Card ─── */
function KpiCard({ label, value, icon: Icon, color, trend }: {
  label: string; value: string | number; icon: React.ElementType; color: string;
  trend?: 'up' | 'down' | 'flat';
}) {
  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-red-500' : 'text-slate-400';
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className={`p-1.5 rounded-lg ${color}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
        {trend && <TrendIcon className={`w-4 h-4 ${trendColor}`} />}
      </div>
      <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{label}</p>
    </div>
  );
}

/* ─── Tooltip styling ─── */
const tooltipStyle = {
  background: '#1e293b', border: 'none', borderRadius: '8px',
  color: '#f1f5f9', fontSize: '12px',
};

/* ─── Section wrapper ─── */
function Section({ title, icon: Icon, iconColor, children, action }: {
  title: string; icon: React.ElementType; iconColor: string;
  children: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 sm:p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <Icon className={`w-4 h-4 ${iconColor}`} /> {title}
        </h3>
        {action}
      </div>
      {children}
    </div>
  );
}

/* ─── Helpers ─── */
function fmtDuration(ms: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

/* ════════════════════════════════════════════════════════════
 *  MAIN PAGE
 * ════════════════════════════════════════════════════════════ */
export default function ReportsPage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<ExecutionOverview | null>(null);
  const [timeline, setTimeline] = useState<ExecutionTimeline | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowPerformanceEntry[]>([]);
  const [summary, setSummary] = useState<SummaryRow[]>([]);

  // Looker Studio
  const [lookerUrl, setLookerUrl] = useState(() =>
    localStorage.getItem('rpa_looker_url') || ''
  );
  const [lookerInput, setLookerInput] = useState(lookerUrl);
  const [showLookerConfig, setShowLookerConfig] = useState(false);

  // Sheets sync
  const [sheetsId, setSheetsId] = useState(() =>
    localStorage.getItem('rpa_sheets_id') || ''
  );
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Download state
  const [downloading, setDownloading] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, tl, wf, sm] = await Promise.all([
        fetchExecutionOverview(days).catch(() => null),
        fetchExecutionTimeline(days, days <= 7 ? 'day' : 'day').catch(() => null),
        fetchWorkflowPerformance(days, 20).catch(() => null),
        fetchDailySummary(days).catch(() => null),
      ]);
      setOverview(ov);
      setTimeline(tl);
      setWorkflows(wf?.workflows || []);
      setSummary(sm?.rows || []);
    } catch { /* */ }
    finally { setLoading(false); }
  }, [days]);

  useEffect(() => { loadAll(); }, [loadAll]);

  /* ─── Chart data ─── */
  const trendData = useMemo(() =>
    summary.map((r) => ({
      date: new Date(r.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      total: r.total,
      completed: r.completed,
      failed: r.failed,
      rate: r.success_rate,
    }))
  , [summary]);

  const statusPieData = useMemo(() => {
    if (!overview) return [];
    return [
      { name: 'Completed', value: overview.successful_executions, color: C.emerald },
      { name: 'Failed', value: overview.failed_executions, color: C.red },
      { name: 'Other', value: Math.max(0, overview.total_executions - overview.successful_executions - overview.failed_executions), color: C.slate },
    ].filter((d) => d.value > 0);
  }, [overview]);

  /* ─── Actions ─── */
  const handleDownloadCsv = async (type: 'executions' | 'summary') => {
    setDownloading(true);
    try {
      const resp = await client.get(`/analytics/export/${type}`, {
        params: { days, format: 'csv' },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_${days}d.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* */ }
    finally { setDownloading(false); }
  };

  const handleSheetsSync = async () => {
    if (!sheetsId.trim()) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await syncToGoogleSheets(sheetsId.trim());
      setSyncResult(`Synced ${result.rows_written} rows`);
      localStorage.setItem('rpa_sheets_id', sheetsId.trim());
    } catch (e: any) {
      setSyncResult(`Error: ${e.response?.data?.detail || e.message}`);
    } finally { setSyncing(false); }
  };

  const saveLookerUrl = () => {
    setLookerUrl(lookerInput.trim());
    localStorage.setItem('rpa_looker_url', lookerInput.trim());
    setShowLookerConfig(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-indigo-500" /> Reports & Analytics
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Execution trends, performance insights, and data export
          </p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodSelector value={days} onChange={setDays} />
          <button onClick={loadAll} className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition" title="Refresh">
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <KpiCard label="Total Executions" value={overview?.total_executions ?? 0}
          icon={Activity} color="bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400" />
        <KpiCard label="Success Rate" value={`${overview?.success_rate?.toFixed(1) ?? 0}%`}
          icon={CheckCircle2} color="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
          trend={(overview?.success_rate ?? 0) >= 80 ? 'up' : 'down'} />
        <KpiCard label="Failed" value={overview?.failed_executions ?? 0}
          icon={XCircle} color="bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400" />
        <KpiCard label="Avg Duration" value={fmtDuration(overview?.average_duration_ms ?? 0)}
          icon={Clock} color="bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400" />
      </div>

      {/* ── Row: Execution Trend + Status Distribution ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Chart */}
        <div className="lg:col-span-2">
          <Section title="Execution Trend" icon={TrendingUp} iconColor="text-indigo-500">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={trendData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={C.emerald} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={C.emerald} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} domain={[0, 100]} unit="%" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Area yAxisId="left" type="monotone" dataKey="completed" name="Completed" stroke={C.emerald} strokeWidth={2} fillOpacity={1} fill="url(#gradCompleted)" />
                  <Bar yAxisId="left" dataKey="failed" name="Failed" fill={C.red} radius={[3, 3, 0, 0]} barSize={12} />
                  <Line yAxisId="right" type="monotone" dataKey="rate" name="Success %" stroke={C.indigo} strokeWidth={2} dot={false} strokeDasharray="5 5" />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-sm text-slate-400">
                No data for this period
              </div>
            )}
          </Section>
        </div>

        {/* Status Distribution Pie */}
        <Section title="Status Distribution" icon={PieIcon} iconColor="text-violet-500">
          {statusPieData.length > 0 ? (
            <div className="flex flex-col items-center">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={statusPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                    dataKey="value" strokeWidth={0} paddingAngle={2}>
                    {statusPieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-slate-400">No data</div>
          )}
        </Section>
      </div>

      {/* ── Workflow Performance Table ── */}
      <Section title="Workflow Performance" icon={Table2} iconColor="text-blue-500">
        {workflows.length > 0 ? (
          <div className="overflow-x-auto -mx-4 sm:-mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700">
                  <th className="text-left px-4 sm:px-5 py-2 text-xs font-semibold text-slate-500 uppercase">Robot</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Runs</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase hidden sm:table-cell">OK</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase hidden sm:table-cell">Fail</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Rate</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Avg Time</th>
                  <th className="text-right px-4 sm:px-5 py-2 text-xs font-semibold text-slate-500 uppercase hidden lg:table-cell">Last Run</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
                {workflows.map((wf) => (
                  <tr key={wf.workflow_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                    <td className="px-4 sm:px-5 py-3 font-medium text-slate-900 dark:text-white max-w-[200px] truncate">{wf.workflow_name}</td>
                    <td className="px-3 py-3 text-right text-slate-700 dark:text-slate-300">{wf.execution_count}</td>
                    <td className="px-3 py-3 text-right text-emerald-600 hidden sm:table-cell">{wf.success_count}</td>
                    <td className="px-3 py-3 text-right text-red-500 hidden sm:table-cell">{wf.failure_count}</td>
                    <td className="px-3 py-3 text-right">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                        wf.success_rate >= 90 ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : wf.success_rate >= 70 ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                        : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>{wf.success_rate.toFixed(0)}%</span>
                    </td>
                    <td className="px-3 py-3 text-right text-slate-500 hidden md:table-cell">{fmtDuration(wf.average_duration_ms)}</td>
                    <td className="px-4 sm:px-5 py-3 text-right text-xs text-slate-400 hidden lg:table-cell">
                      {wf.last_execution ? new Date(wf.last_execution).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-sm text-slate-400">No workflows with executions in this period</div>
        )}
      </Section>

      {/* ── Looker Studio Embed ── */}
      <Section title="Looker Studio Report" icon={BarChart3} iconColor="text-violet-500"
        action={
          <button onClick={() => setShowLookerConfig(!showLookerConfig)}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
            <Settings2 className="w-4 h-4 text-slate-400" />
          </button>
        }>
        {showLookerConfig && (
          <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg space-y-3">
            <p className="text-xs text-slate-500">
              Paste your Looker Studio embed URL. Go to your report → File → Embed report → Copy embed URL.
            </p>
            <div className="flex gap-2">
              <input type="text" value={lookerInput} onChange={(e) => setLookerInput(e.target.value)}
                placeholder="https://lookerstudio.google.com/embed/reporting/..."
                className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
              <button onClick={saveLookerUrl}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition">
                Save
              </button>
            </div>
          </div>
        )}

        {lookerUrl ? (
          <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
            <iframe
              src={lookerUrl}
              className="absolute inset-0 w-full h-full rounded-lg border border-slate-200 dark:border-slate-700"
              frameBorder="0"
              allowFullScreen
              sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            />
          </div>
        ) : (
          <div className="text-center py-12">
            <BarChart3 className="w-12 h-12 text-slate-200 dark:text-slate-700 mx-auto mb-3" />
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">No Looker Studio report configured</p>
            <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
              Connect a Google Sheet as your data source in Looker Studio, then embed the report here for real-time BI dashboards.
            </p>
            <button onClick={() => setShowLookerConfig(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition">
              <Link2 className="w-4 h-4" /> Configure Looker Studio
            </button>
          </div>
        )}
      </Section>

      {/* ── Data Export & Google Sheets Sync ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CSV Export */}
        <Section title="Export Data" icon={Download} iconColor="text-emerald-500">
          <div className="space-y-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Download execution data as CSV files for use in any BI tool.
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <button onClick={() => handleDownloadCsv('summary')} disabled={downloading}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm font-medium rounded-lg transition">
                {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Daily Summary CSV
              </button>
              <button onClick={() => handleDownloadCsv('executions')} disabled={downloading}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg transition">
                {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                All Executions CSV
              </button>
            </div>
          </div>
        </Section>

        {/* Google Sheets Sync */}
        <Section title="Google Sheets Sync" icon={FileSpreadsheet} iconColor="text-green-500">
          <div className="space-y-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Push analytics data to Google Sheets — use as Looker Studio data source.
            </p>
            <div className="flex gap-2">
              <input type="text" value={sheetsId} onChange={(e) => setSheetsId(e.target.value)}
                placeholder="Google Spreadsheet ID"
                className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
              <button onClick={handleSheetsSync} disabled={syncing || !sheetsId.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm font-medium rounded-lg transition">
                {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Sync
              </button>
            </div>
            {syncResult && (
              <p className={`text-xs ${syncResult.startsWith('Error') ? 'text-red-500' : 'text-emerald-600'}`}>
                {syncResult}
              </p>
            )}
            <p className="text-[10px] text-slate-400">
              Find your Spreadsheet ID in the Google Sheets URL: docs.google.com/spreadsheets/d/<strong>SPREADSHEET_ID</strong>/edit
            </p>
          </div>
        </Section>
      </div>

      {/* ── Setup Guide ── */}
      <Section title="Looker Studio Setup Guide" icon={ExternalLink} iconColor="text-indigo-500">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
            <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/40 rounded-lg flex items-center justify-center mb-3">
              <span className="text-sm font-bold text-indigo-600">1</span>
            </div>
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">Sync Data</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enter your Google Spreadsheet ID above and click Sync. This pushes 90 days of analytics data to the sheet.
            </p>
          </div>
          <div className="p-4 bg-violet-50 dark:bg-violet-900/20 rounded-lg">
            <div className="w-8 h-8 bg-violet-100 dark:bg-violet-900/40 rounded-lg flex items-center justify-center mb-3">
              <span className="text-sm font-bold text-violet-600">2</span>
            </div>
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">Create Report</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Open Looker Studio, add your Google Sheet as a data source, and build charts with the synced data.
            </p>
          </div>
          <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
            <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900/40 rounded-lg flex items-center justify-center mb-3">
              <span className="text-sm font-bold text-emerald-600">3</span>
            </div>
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">Embed Here</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              In Looker Studio go to File → Embed → copy the URL and paste it in the config above.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
