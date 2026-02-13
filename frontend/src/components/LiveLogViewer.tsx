/**
 * LiveLogViewer — Real-time execution log viewer using WebSocket.
 *
 * Subscribes to execution.log events via WebSocket for live streaming,
 * with initial fetch of existing logs. Auto-scrolls to bottom.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Loader2,
  Wifi,
  WifiOff,
  Download,
  Trash2,
  ArrowDown,
  Search,
  Filter,
} from 'lucide-react';
import type { ExecutionLog } from '@/types';
import { executionApi } from '@/api/executions';
import { useWebSocket, type ExecutionLogPayload } from '@/hooks/useWebSocket';

const LEVEL_COLORS: Record<string, { text: string; badge: string }> = {
  DEBUG: { text: 'text-slate-400', badge: 'bg-slate-700 text-slate-300' },
  INFO: { text: 'text-blue-400', badge: 'bg-blue-900/50 text-blue-300' },
  WARNING: { text: 'text-amber-400', badge: 'bg-amber-900/50 text-amber-300' },
  ERROR: { text: 'text-red-400', badge: 'bg-red-900/50 text-red-300' },
  CRITICAL: { text: 'text-red-500 font-bold', badge: 'bg-red-800 text-red-200' },
};

interface Props {
  executionId: string;
  isRunning?: boolean;
}

export default function LiveLogViewer({ executionId, isRunning = false }: Props) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const { readyState, on } = useWebSocket();

  // Fetch initial logs
  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await executionApi.logs(executionId);
        setLogs(Array.isArray(data) ? data : []);
      } catch {
        setLogs([]);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [executionId]);

  // Subscribe to WebSocket log events
  useEffect(() => {
    const unsubscribe = on('execution.log', (payload) => {
      const data = payload as ExecutionLogPayload;
      if (data.execution_id === executionId) {
        const newLog: ExecutionLog = {
          id: `ws_${Date.now()}_${Math.random()}`,
          level: data.level,
          message: data.message,
          timestamp: data.timestamp,
        };
        setLogs((prev) => [...prev, newLog]);
      }
    });
    return unsubscribe;
  }, [executionId, on]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Detect manual scroll
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  }, []);

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
      setAutoScroll(true);
    }
  };

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    if (levelFilter && log.level !== levelFilter) return false;
    if (filter && !log.message.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  // Export logs as text
  const handleExport = () => {
    const text = filteredLogs
      .map((l) => `[${new Date(l.timestamp).toISOString()}] [${l.level}] ${l.message}`)
      .join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-${executionId.slice(0, 8)}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="py-6 flex justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800 rounded-t-lg border border-slate-700 border-b-0">
        <div className="flex items-center gap-2">
          {/* WebSocket indicator */}
          <span className="flex items-center gap-1 text-[10px]">
            {readyState === 'open' ? (
              <><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-emerald-400">Live</span></>
            ) : (
              <><WifiOff className="w-3 h-3 text-slate-500" /><span className="text-slate-500">Offline</span></>
            )}
          </span>

          {/* Log count */}
          <span className="text-[10px] text-slate-500">{filteredLogs.length} log{filteredLogs.length !== 1 ? 's' : ''}</span>

          {isRunning && (
            <span className="flex items-center gap-1 text-[10px] text-blue-400">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" /> streaming
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter..."
              className="w-28 pl-6 pr-2 py-1 text-[10px] bg-slate-700 border border-slate-600 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/30"
            />
          </div>

          {/* Level filter */}
          <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}
            className="text-[10px] py-1 px-1.5 bg-slate-700 border border-slate-600 rounded text-slate-200">
            <option value="">All levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>

          {/* Export */}
          <button onClick={handleExport} className="p-1 text-slate-500 hover:text-slate-300" title="Export logs">
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Log output */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-slate-900 rounded-b-lg border border-slate-700 p-3 max-h-80 overflow-y-auto font-mono text-xs space-y-0.5 relative"
      >
        {filteredLogs.length === 0 ? (
          <p className="text-slate-500 text-center py-4">
            {logs.length === 0 ? 'No logs available' : 'No logs match filter'}
          </p>
        ) : (
          filteredLogs.map((log, idx) => {
            const lc = LEVEL_COLORS[log.level] || LEVEL_COLORS.INFO;
            return (
              <div key={log.id || idx} className="flex gap-2 hover:bg-slate-800/50 rounded px-1 -mx-1">
                <span className="text-slate-600 flex-shrink-0 select-none">
                  {new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 } as any)}
                </span>
                <span className={`flex-shrink-0 w-16 text-right ${lc.text}`}>[{log.level}]</span>
                <span className="text-slate-200 break-all">{log.message}</span>
              </div>
            );
          })
        )}

        {/* Scroll to bottom button */}
        {!autoScroll && filteredLogs.length > 10 && (
          <button
            onClick={scrollToBottom}
            className="sticky bottom-0 left-1/2 -translate-x-1/2 flex items-center gap-1 px-3 py-1 text-[10px] text-white bg-indigo-600 rounded-full shadow-lg hover:bg-indigo-700 transition"
          >
            <ArrowDown className="w-3 h-3" /> Scroll to bottom
          </button>
        )}
      </div>
    </div>
  );
}
