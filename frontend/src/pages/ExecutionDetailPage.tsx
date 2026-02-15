/**
 * ExecutionDetailPage — Full execution detail view with step-by-step progress.
 *
 * Shows execution metadata, step timeline with status indicators,
 * progress bar, collapsible step cards, live log viewer, and variable context.
 * Includes a "Results Data" tab for viewing scraped data in a table with export.
 */

import { useEffect, useState, useCallback, useMemo, Fragment } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
  Ban,
  Loader2,
  RotateCcw,
  Play,
  Timer,
  Hash,
  GitBranch,
  Server,
  Calendar,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Zap,
  Code2,
  Check,
  Download,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Table2,
  FileJson,
  FileSpreadsheet,
  Database,
  Eye,
  X,
} from 'lucide-react';
import type { Execution } from '@/types';
import { executionApi } from '@/api/executions';
import { useWebSocket, type ExecutionStatusPayload } from '@/hooks/useWebSocket';
import LiveLogViewer from '@/components/LiveLogViewer';
import { useLocale } from '@/i18n';

/* ─── Status config ─── */
const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; border: string; textColor: string; barColor: string }> = {
  pending:   { icon: Clock,        color: 'text-amber-600',   bg: 'bg-amber-50 dark:bg-amber-900/20',   border: 'border-amber-200 dark:border-amber-800',   textColor: 'text-amber-700 dark:text-amber-400',   barColor: 'bg-amber-400' },
  running:   { icon: Activity,     color: 'text-blue-600',    bg: 'bg-blue-50 dark:bg-blue-900/20',     border: 'border-blue-200 dark:border-blue-800',     textColor: 'text-blue-700 dark:text-blue-400',     barColor: 'bg-blue-500' },
  completed: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800', textColor: 'text-emerald-700 dark:text-emerald-400', barColor: 'bg-emerald-500' },
  failed:    { icon: XCircle,      color: 'text-red-600',     bg: 'bg-red-50 dark:bg-red-900/20',       border: 'border-red-200 dark:border-red-800',       textColor: 'text-red-700 dark:text-red-400',       barColor: 'bg-red-500' },
  cancelled: { icon: Ban,          color: 'text-slate-500',   bg: 'bg-slate-50 dark:bg-slate-800',      border: 'border-slate-200 dark:border-slate-700',   textColor: 'text-slate-600 dark:text-slate-400',   barColor: 'bg-slate-400' },
  skipped:   { icon: ChevronRight, color: 'text-slate-400',   bg: 'bg-slate-50 dark:bg-slate-800',      border: 'border-slate-200 dark:border-slate-700',   textColor: 'text-slate-500 dark:text-slate-500',   barColor: 'bg-slate-300' },
};

function StatusBadge({ status, large }: { status: string; large?: boolean }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${cfg.bg} ${cfg.color} ${cfg.border} ${large ? 'px-4 py-1.5 text-sm' : 'px-2.5 py-1 text-xs'}`}>
      <Icon className={large ? 'w-4 h-4' : 'w-3 h-3'} />
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

function formatDatetime(iso?: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

/* ─── Copy button ─── */
function CopyButton({ text, size = 'sm' }: { text: string; size?: 'sm' | 'xs' }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  const iconSize = size === 'xs' ? 'w-3 h-3' : 'w-3.5 h-3.5';
  return (
    <button onClick={handleCopy} className="p-0.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition" title="Copy">
      {copied ? <Check className={`${iconSize} text-emerald-500`} /> : <Copy className={iconSize} />}
    </button>
  );
}

/* ─── Elapsed time counter ─── */
function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState('');
  useEffect(() => {
    const start = new Date(startedAt).getTime();
    const update = () => {
      const diff = Date.now() - start;
      setElapsed(formatDuration(diff));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);
  return <span className="text-blue-600 dark:text-blue-400 font-mono text-sm animate-pulse">{elapsed}</span>;
}

/* ─── Metadata card ─── */
function MetaItem({ icon: Icon, label, value, mono }: { icon: React.ElementType; label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</p>
        <p className={`text-sm text-slate-900 dark:text-white truncate ${mono ? 'font-mono text-xs' : ''}`}>{value}</p>
      </div>
    </div>
  );
}

/* ─── Overall progress bar ─── */
function ProgressBar({ steps }: { steps: StepInfo[] }) {
  if (steps.length === 0) return null;
  const completed = steps.filter((s) => s.status === 'completed').length;
  const failed = steps.filter((s) => s.status === 'failed').length;
  const running = steps.filter((s) => s.status === 'running').length;
  const pct = Math.round(((completed + failed) / steps.length) * 100);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          Overall Progress
        </span>
        <span className="text-xs font-mono text-slate-500">
          {completed}/{steps.length} steps
          {failed > 0 && <span className="text-red-500 ml-1">({failed} failed)</span>}
          {running > 0 && <span className="text-blue-500 ml-1">({running} running)</span>}
        </span>
      </div>
      <div className="h-2.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            failed > 0 ? 'bg-gradient-to-r from-emerald-500 to-red-500' :
            pct === 100 ? 'bg-emerald-500' : 'bg-blue-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[10px] text-slate-400 mt-1 text-right">{pct}%</p>
    </div>
  );
}

/* ─── Step duration bar ─── */
function StepDurationBar({ durationMs, totalMs }: { durationMs: number; totalMs: number }) {
  const pct = totalMs > 0 ? Math.max(2, Math.round((durationMs / totalMs) * 100)) : 0;
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-400 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[9px] text-slate-400 font-mono w-8 text-right">{pct}%</span>
    </div>
  );
}

/* ─── Step timeline (collapsible cards) ─── */
interface StepInfo {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
}

function StepTimeline({ steps, totalDurationMs }: { steps: StepInfo[]; totalDurationMs: number }) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  if (steps.length === 0) {
    return (
      <div className="text-center py-8">
        <GitBranch className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-400">No step data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        const statusCfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.pending;
        const Icon = statusCfg.icon;
        const isExpanded = expandedStep === step.id;
        const hasDetails = step.error || step.input || step.output || step.started_at;

        return (
          <div key={step.id} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${statusCfg.bg} ${statusCfg.border} border`}>
                {step.status === 'running' ? (
                  <Loader2 className={`w-3.5 h-3.5 ${statusCfg.color} animate-spin`} />
                ) : (
                  <Icon className={`w-3.5 h-3.5 ${statusCfg.color}`} />
                )}
              </div>
              {!isLast && <div className="w-px flex-1 bg-slate-200 dark:bg-slate-700 my-1" />}
            </div>

            {/* Step content */}
            <div className={`flex-1 pb-3 ${isLast ? '' : ''}`}>
              <div
                className={`rounded-lg border ${isExpanded ? 'border-indigo-200 dark:border-indigo-800 bg-slate-50 dark:bg-slate-800/50' : 'border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/30'} px-3 py-2 transition ${hasDetails ? 'cursor-pointer' : ''}`}
                onClick={() => hasDetails && setExpandedStep(isExpanded ? null : step.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    {hasDetails && (
                      <ChevronRight className={`w-3 h-3 text-slate-400 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`} />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                        <span className="text-slate-400 text-xs mr-1.5">#{idx + 1}</span>
                        {step.name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                          <Code2 className="w-2.5 h-2.5" />{step.type}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-2">
                    <p className={`text-xs font-medium ${statusCfg.textColor}`}>{step.status}</p>
                    {step.duration_ms != null && (
                      <p className="text-[10px] text-slate-400 font-mono">{formatDuration(step.duration_ms)}</p>
                    )}
                  </div>
                </div>

                {/* Duration bar */}
                {step.duration_ms != null && totalDurationMs > 0 && (
                  <StepDurationBar durationMs={step.duration_ms} totalMs={totalDurationMs} />
                )}

                {/* Error preview (always visible) */}
                {step.error && !isExpanded && (
                  <div className="mt-1.5 text-[10px] text-red-500 truncate">{step.error}</div>
                )}
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="mt-1 ml-5 space-y-2 animate-in slide-in-from-top-1 duration-200">
                  {/* Timestamps */}
                  {step.started_at && (
                    <div className="flex gap-4 text-[10px] text-slate-400">
                      <span>Started: {formatDatetime(step.started_at)}</span>
                      {step.completed_at && <span>Ended: {formatDatetime(step.completed_at)}</span>}
                    </div>
                  )}

                  {/* Error with copy */}
                  {step.error && (
                    <div className="text-[11px] text-red-500 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded px-2.5 py-2 font-mono whitespace-pre-wrap relative group">
                      <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition">
                        <CopyButton text={step.error} size="xs" />
                      </div>
                      {step.error}
                    </div>
                  )}

                  {/* Input data */}
                  {step.input && Object.keys(step.input).length > 0 && (
                    <details className="text-[10px]">
                      <summary className="text-slate-500 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 font-medium">
                        Input Data
                      </summary>
                      <pre className="mt-1 p-2 bg-slate-50 dark:bg-slate-900 rounded text-slate-600 dark:text-slate-300 overflow-x-auto font-mono">
                        {JSON.stringify(step.input, null, 2)}
                      </pre>
                    </details>
                  )}

                  {/* Output data */}
                  {step.output && Object.keys(step.output).length > 0 && (
                    <details className="text-[10px]">
                      <summary className="text-slate-500 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300 font-medium">
                        Output Data
                      </summary>
                      <pre className="mt-1 p-2 bg-slate-50 dark:bg-slate-900 rounded text-slate-600 dark:text-slate-300 overflow-x-auto font-mono">
                        {JSON.stringify(step.output, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Data Tab: Results viewer with table, search, sort, export ─── */

interface DataRow {
  [key: string]: any;
}

interface DataSource {
  stepId: string;
  label: string;
  rows: DataRow[];
  columns: string[];
}

/** Find all arrays of objects in step outputs */
function extractDataSources(stepsData: Record<string, any>): DataSource[] {
  const sources: DataSource[] = [];

  /** Recursively search an object for tabular data */
  function searchObject(obj: any, stepId: string, pathLabel: string) {
    if (!obj || typeof obj !== 'object') return;

    // 1) Direct array of objects: [{title: "...", price: "..."}, ...]
    if (Array.isArray(obj) && obj.length > 0 && typeof obj[0] === 'object' && !Array.isArray(obj[0])) {
      const columns = [...new Set(obj.flatMap((row: any) => Object.keys(row)))];
      sources.push({ stepId, label: pathLabel, rows: obj, columns });
      return;
    }

    // 2) Check nested keys
    if (!Array.isArray(obj)) {
      // Collect parallel arrays of primitives (e.g., deal_titles: [...], deal_prices: [...])
      const parallelArrays: Record<string, any[]> = {};
      let maxLen = 0;

      for (const [key, val] of Object.entries(obj)) {
        if (Array.isArray(val) && val.length > 0) {
          if (typeof val[0] === 'object' && !Array.isArray(val[0])) {
            // Array of objects — treat as a data source directly
            const rows = val as DataRow[];
            const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
            sources.push({ stepId, label: `${pathLabel} / ${key}`, rows, columns });
          } else if (typeof val[0] !== 'object') {
            // Array of primitives — candidate for parallel array zip
            parallelArrays[key] = val;
            maxLen = Math.max(maxLen, val.length);
          }
        } else if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
          // Recurse into nested objects (e.g., output.data.deals)
          searchObject(val, stepId, `${pathLabel} / ${key}`);
        }
      }

      // Zip parallel arrays into rows if we have 2+ arrays of similar length
      const arrayKeys = Object.keys(parallelArrays);
      if (arrayKeys.length >= 2 && maxLen > 0) {
        // Only zip arrays that have at least 50% of maxLen (filter out tiny metadata arrays)
        const zippableKeys = arrayKeys.filter(k => parallelArrays[k].length >= maxLen * 0.5);
        if (zippableKeys.length >= 2) {
          const rows: DataRow[] = [];
          for (let i = 0; i < maxLen; i++) {
            const row: DataRow = {};
            for (const key of zippableKeys) {
              row[key] = parallelArrays[key][i] ?? null;
            }
            rows.push(row);
          }
          sources.push({ stepId, label: pathLabel, rows, columns: zippableKeys });
        }
      }
    }
  }

  for (const [stepId, stepInfo] of Object.entries(stepsData)) {
    const output = stepInfo?.output;
    if (!output) continue;
    searchObject(output, stepId, stepId);
  }

  // Sort by row count descending — largest dataset first
  sources.sort((a, b) => b.rows.length - a.rows.length);
  return sources;
}

/** Smart column label */
function columnLabel(key: string): string {
  const labels: Record<string, string> = {
    r: 'Rank', t: 'Title', p: 'Price', rt: 'Rating',
    a: 'ASIN', c: 'Category', u: 'URL',
    rank: 'Rank', title: 'Title', price: 'Price', rating: 'Rating',
    asin: 'ASIN', category: 'Category', url: 'URL', name: 'Name',
    description: 'Description', brand: 'Brand', model: 'Model',
  };
  return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Preferred column order */
function columnOrder(key: string): number {
  const order: Record<string, number> = {
    r: 0, rank: 0, t: 1, title: 1, name: 1,
    p: 2, price: 2, rt: 3, rating: 3,
    c: 4, category: 4, a: 5, asin: 5,
    brand: 6, model: 7, u: 99, url: 99,
  };
  return order[key] ?? 50;
}

/** Export to CSV */
function exportCSV(rows: DataRow[], columns: string[], filename: string) {
  const header = columns.map(columnLabel).join(',');
  const body = rows.map((row) =>
    columns.map((col) => {
      const val = String(row[col] ?? '');
      return val.includes(',') || val.includes('"') || val.includes('\n')
        ? `"${val.replace(/"/g, '""')}"`
        : val;
    }).join(',')
  ).join('\n');

  const blob = new Blob([header + '\n' + body], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Export to JSON */
function exportJSON(data: any, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function DataTab({ executionId }: { executionId: string }) {
  const [stepsData, setStepsData] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    executionApi.data(executionId)
      .then((resp) => {
        setStepsData(resp.steps || {});
      })
      .catch((err) => {
        setError(err?.message || 'Failed to load execution data');
      })
      .finally(() => setLoading(false));
  }, [executionId]);

  const dataSources = useMemo(() => {
    if (!stepsData) return [];
    return extractDataSources(stepsData);
  }, [stepsData]);

  const currentSource = dataSources[selectedSource];

  const sortedColumns = useMemo(() => {
    if (!currentSource) return [];
    return [...currentSource.columns].sort((a, b) => columnOrder(a) - columnOrder(b));
  }, [currentSource]);

  // Columns to show in the table (exclude URL — too long)
  const tableColumns = useMemo(() => {
    return sortedColumns.filter((c) => !['u', 'url', 'description'].includes(c));
  }, [sortedColumns]);

  const filteredRows = useMemo(() => {
    if (!currentSource) return [];
    let rows = currentSource.rows;

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      rows = rows.filter((row) =>
        Object.values(row).some((val) => String(val).toLowerCase().includes(q))
      );
    }

    // Sort
    if (sortColumn) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortColumn];
        const bv = b[sortColumn];
        // Try numeric sort
        const an = parseFloat(av);
        const bn = parseFloat(bv);
        if (!isNaN(an) && !isNaN(bn)) {
          return sortDir === 'asc' ? an - bn : bn - an;
        }
        // String sort
        const sa = String(av || '').toLowerCase();
        const sb = String(bv || '').toLowerCase();
        return sortDir === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa);
      });
    }

    return rows;
  }, [currentSource, searchQuery, sortColumn, sortDir]);

  const handleSort = (col: string) => {
    if (sortColumn === col) {
      setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('asc');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
        <span className="ml-2 text-sm text-slate-500">Loading results data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <XCircle className="w-4 h-4 text-red-500" />
        <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
      </div>
    );
  }

  if (dataSources.length === 0) {
    return (
      <div className="text-center py-12">
        <Database className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
        <p className="text-sm text-slate-500 dark:text-slate-400">No structured data found in step outputs</p>
        <p className="text-xs text-slate-400 mt-1">Execute the workflow to generate results</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toolbar: source selector, search, export */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Source selector */}
        {dataSources.length > 1 && (
          <select
            value={selectedSource}
            onChange={(e) => { setSelectedSource(Number(e.target.value)); setSearchQuery(''); setSortColumn(null); setExpandedRow(null); }}
            className="text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-1.5 text-slate-700 dark:text-slate-300"
          >
            {dataSources.map((src, i) => (
              <option key={i} value={i}>{src.label} ({src.rows.length} rows)</option>
            ))}
          </select>
        )}

        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search results..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2">
              <X className="w-3 h-3 text-slate-400 hover:text-slate-600" />
            </button>
          )}
        </div>

        {/* Row count */}
        <span className="text-xs text-slate-400">
          {filteredRows.length} of {currentSource.rows.length} rows
        </span>

        {/* Export buttons */}
        <div className="flex items-center gap-1 ml-auto">
          <button
            onClick={() => exportCSV(filteredRows, sortedColumns, `execution-${executionId.slice(0, 8)}.csv`)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition text-slate-600 dark:text-slate-300"
            title="Download CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" /> CSV
          </button>
          <button
            onClick={() => exportJSON(filteredRows, `execution-${executionId.slice(0, 8)}.json`)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition text-slate-600 dark:text-slate-300"
            title="Download JSON"
          >
            <FileJson className="w-3.5 h-3.5" /> JSON
          </button>
        </div>
      </div>

      {/* Data table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider w-8">#</th>
                {tableColumns.map((col) => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400 transition select-none"
                  >
                    <span className="inline-flex items-center gap-1">
                      {columnLabel(col)}
                      {sortColumn === col ? (
                        sortDir === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-2.5 h-2.5 opacity-30" />
                      )}
                    </span>
                  </th>
                ))}
                <th className="px-3 py-2.5 w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {filteredRows.map((row, idx) => {
                const isExpanded = expandedRow === idx;
                return (
                  <Fragment key={idx}>
                    <tr
                      className={`hover:bg-slate-50 dark:hover:bg-slate-800/50 transition ${isExpanded ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}`}
                    >
                      <td className="px-3 py-2 text-xs text-slate-400 font-mono">{idx + 1}</td>
                      {tableColumns.map((col) => {
                        const val = row[col];
                        const isUrl = typeof val === 'string' && val.startsWith('http');
                        const isNum = typeof val === 'number' || (!isNaN(parseFloat(val)) && isFinite(val));
                        return (
                          <td key={col} className={`px-3 py-2 text-slate-700 dark:text-slate-300 ${isNum ? 'font-mono tabular-nums' : ''}`}>
                            {isUrl ? (
                              <a href={val} target="_blank" rel="noopener noreferrer"
                                className="text-indigo-500 hover:text-indigo-600 inline-flex items-center gap-1 text-xs">
                                Link <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            ) : (
                              <span className="block truncate max-w-[300px]" title={String(val ?? '')}>
                                {String(val ?? '—')}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td className="px-2 py-2">
                        <button
                          onClick={() => setExpandedRow(isExpanded ? null : idx)}
                          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition"
                          title="View details"
                        >
                          <Eye className={`w-3.5 h-3.5 ${isExpanded ? 'text-indigo-500' : 'text-slate-400'}`} />
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={tableColumns.length + 2} className="px-6 py-3 bg-slate-50 dark:bg-slate-900/30">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                            {sortedColumns.map((col) => (
                              <div key={col}>
                                <span className="text-slate-400 text-[10px] uppercase">{columnLabel(col)}</span>
                                <p className="text-slate-700 dark:text-slate-300 mt-0.5 break-all">
                                  {typeof row[col] === 'string' && row[col]?.startsWith('http') ? (
                                    <a href={row[col]} target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:underline">
                                      {row[col]}
                                    </a>
                                  ) : (
                                    String(row[col] ?? '—')
                                  )}
                                </p>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={tableColumns.length + 2} className="px-4 py-8 text-center text-sm text-slate-400">
                    {searchQuery ? 'No results match your search' : 'No data available'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─── */
export default function ExecutionDetailPage() {
  const { t } = useLocale();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [steps, setSteps] = useState<StepInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'data'>('overview');
  const { on } = useWebSocket();

  const fetchExecution = useCallback(async () => {
    if (!id) return;
    try {
      const data = await executionApi.get(id);
      setExecution(data);

      // Try to extract step info from execution metadata
      const meta = (data as any).steps || (data as any).step_results || [];
      if (Array.isArray(meta) && meta.length > 0) {
        setSteps(meta.map((s: any) => ({
          id: s.id || s.step_id || `step_${Math.random()}`,
          name: s.name || s.step_name || s.type || 'Unknown',
          type: s.type || s.step_type || 'unknown',
          status: s.status || 'pending',
          started_at: s.started_at,
          completed_at: s.completed_at,
          duration_ms: s.duration_ms,
          error: s.error || s.error_message,
          input: s.input || s.input_data,
          output: s.output || s.output_data || s.result,
        })));
      }
    } catch {
      navigate('/executions');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchExecution();
  }, [fetchExecution]);

  // Live status updates
  useEffect(() => {
    const unsubscribe = on('execution.status_changed', (payload) => {
      const data = payload as ExecutionStatusPayload;
      if (data.execution_id === id) {
        setExecution((prev) => prev ? { ...prev, status: data.status as Execution['status'] } : prev);
        // Re-fetch for updated step data
        fetchExecution();
      }
    });
    return unsubscribe;
  }, [id, on, fetchExecution]);

  // Auto-refresh for running executions
  useEffect(() => {
    if (!execution || (execution.status !== 'running' && execution.status !== 'pending')) return;
    const interval = setInterval(fetchExecution, 3000);
    return () => clearInterval(interval);
  }, [execution, fetchExecution]);

  const totalStepDuration = useMemo(() =>
    steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0),
    [steps]
  );

  const handleRetry = async () => {
    if (!id) return;
    try {
      await executionApi.retry(id);
      fetchExecution();
    } catch { /* handle */ }
  };

  const handleCancel = async () => {
    if (!id) return;
    try {
      await executionApi.cancel(id);
      fetchExecution();
    } catch { /* handle */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!execution) return null;

  const isActive = execution.status === 'running' || execution.status === 'pending';
  const isFailed = execution.status === 'failed' || execution.status === 'cancelled';

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/executions')} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
          <ArrowLeft className="w-5 h-5 text-slate-500" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Execution Detail</h1>
            <StatusBadge status={execution.status} large />
            {isActive && execution.started_at && (
              <ElapsedTimer startedAt={execution.started_at} />
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-xs font-mono text-slate-400">{id}</p>
            <CopyButton text={id || ''} size="xs" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isFailed && (
            <button onClick={handleRetry}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition text-slate-600 dark:text-slate-300">
              <RotateCcw className="w-4 h-4" /> Retry
            </button>
          )}
          {isActive && (
            <button onClick={handleCancel}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition text-red-600 dark:text-red-400">
              <Ban className="w-4 h-4" /> Cancel
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-6 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition -mb-px ${
            activeTab === 'overview'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Activity className="w-3.5 h-3.5" /> Overview
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition -mb-px ${
            activeTab === 'data'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Table2 className="w-3.5 h-3.5" /> Results Data
        </button>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' ? (
        <>
          {/* Progress bar */}
          <div className="mb-6">
            <ProgressBar steps={steps} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column: metadata + steps */}
            <div className="lg:col-span-1 space-y-6">
              {/* Metadata card */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">Execution Info</h3>
                <div className="space-y-3.5">
                  <MetaItem icon={Hash} label="Execution ID" value={id || '—'} mono />
                  <MetaItem icon={GitBranch} label="Workflow" value={execution.workflow_id} mono />
                  {execution.agent_id && <MetaItem icon={Server} label="Agent" value={execution.agent_id} mono />}
                  <MetaItem icon={Play} label="Trigger Type" value={execution.trigger_type} />
                  <MetaItem icon={Calendar} label="Started" value={formatDatetime(execution.started_at)} />
                  <MetaItem icon={Calendar} label="Completed" value={formatDatetime(execution.completed_at)} />
                  <MetaItem icon={Timer} label="Duration" value={
                    isActive && execution.started_at ? 'In progress...' : formatDuration(execution.duration_ms)
                  } />
                  {execution.retry_count > 0 && (
                    <MetaItem icon={RotateCcw} label="Retries" value={String(execution.retry_count)} />
                  )}
                </div>

                {execution.workflow_id && (
                  <Link to={`/workflows/${execution.workflow_id}/edit`}
                    className="flex items-center gap-1 mt-4 text-xs text-indigo-500 hover:text-indigo-600 transition">
                    <ExternalLink className="w-3 h-3" /> View Workflow
                  </Link>
                )}
              </div>

              {/* Step timeline */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3 h-3" />
                    Step Progress
                  </h3>
                  {steps.length > 0 && (
                    <span className="text-[10px] font-mono text-slate-400">
                      {steps.filter((s) => s.status === 'completed').length}/{steps.length}
                    </span>
                  )}
                </div>
                <StepTimeline steps={steps} totalDurationMs={totalStepDuration} />
              </div>
            </div>

            {/* Right column: logs + error */}
            <div className="lg:col-span-2 space-y-6">
              {/* Error message */}
              {execution.error_message && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 relative group">
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition">
                    <CopyButton text={execution.error_message} />
                  </div>
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-700 dark:text-red-400">Execution Failed</p>
                      <p className="text-xs text-red-600 dark:text-red-400/80 mt-1 font-mono whitespace-pre-wrap">{execution.error_message}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Live logs */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">Execution Logs</h3>
                <LiveLogViewer executionId={id!} isRunning={execution.status === 'running'} />
              </div>
            </div>
          </div>
        </>
      ) : (
        <DataTab executionId={id!} />
      )}
    </div>
  );
}
