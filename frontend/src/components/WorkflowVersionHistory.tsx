import { useEffect, useState } from 'react';
import { History, User, Clock, ChevronDown, ChevronRight, Copy, RotateCcw } from 'lucide-react';
import client from '@/api/client';

interface HistoryEntry {
  id: string;
  action: string;
  user_email: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  created_at: string;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ActionBadge({ action }: { action: string }) {
  const colors: Record<string, string> = {
    create: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    publish: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
    archive: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    execute: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
    delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    clone: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  };
  return (
    <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${colors[action] || 'bg-slate-100 text-slate-600'}`}>
      {action}
    </span>
  );
}

export default function WorkflowVersionHistory({
  workflowId,
  onClone,
}: {
  workflowId: string;
  onClone?: () => void;
}) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await client.get(`/api/v1/workflows/${workflowId}/history`);
        if (!cancelled) setHistory(data.items || data.history || []);
      } catch {
        // handle
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [workflowId]);

  const handleClone = async () => {
    try {
      await client.post(`/api/v1/workflows/${workflowId}/clone`);
      onClone?.();
    } catch {
      // handle
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-sm text-slate-400">Loading history...</div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <History className="w-4 h-4" />
          Version History
        </div>
        <button
          onClick={handleClone}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 rounded-lg transition"
        >
          <Copy className="w-3 h-3" />
          Clone
        </button>
      </div>

      {history.length === 0 ? (
        <div className="p-6 text-center text-sm text-slate-400">No history available</div>
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-700 max-h-80 overflow-y-auto">
          {history.map((entry) => (
            <div key={entry.id} className="px-4 py-3">
              <button
                onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                className="w-full flex items-center gap-3 text-left"
              >
                {expandedId === entry.id ? (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <ActionBadge action={entry.action} />
                    <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {entry.user_email}
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-slate-400 flex items-center gap-1 shrink-0">
                  <Clock className="w-3 h-3" />
                  {relativeTime(entry.created_at)}
                </span>
              </button>

              {expandedId === entry.id && (entry.old_values || entry.new_values) && (
                <div className="mt-2 ml-6 grid grid-cols-2 gap-2">
                  {entry.old_values && (
                    <div className="bg-red-50 dark:bg-red-900/10 rounded-lg p-2">
                      <div className="text-[10px] font-medium text-red-600 dark:text-red-400 mb-1">Before</div>
                      <pre className="text-[10px] text-red-700 dark:text-red-300 font-mono overflow-x-auto max-h-32">
                        {JSON.stringify(entry.old_values, null, 2)}
                      </pre>
                    </div>
                  )}
                  {entry.new_values && (
                    <div className="bg-emerald-50 dark:bg-emerald-900/10 rounded-lg p-2">
                      <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 mb-1">After</div>
                      <pre className="text-[10px] text-emerald-700 dark:text-emerald-300 font-mono overflow-x-auto max-h-32">
                        {JSON.stringify(entry.new_values, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
