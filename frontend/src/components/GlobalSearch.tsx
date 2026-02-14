/**
 * Global Search — Cmd/Ctrl+K searchable command palette.
 *
 * Searches across workflows, executions, agents, and templates.
 * Opens as a modal overlay with keyboard navigation.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  GitBranch,
  Play,
  Server,
  BookOpen,
  Users,
  FileText,
  X,
  Loader2,
  Command,
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';

/* ─── Types ─── */

interface SearchResult {
  id: string;
  type: 'workflow' | 'execution' | 'agent' | 'template' | 'user';
  title: string;
  subtitle?: string;
  url: string;
}

interface GlobalSearchProps {
  onClose: () => void;
}

const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  workflow: { icon: GitBranch, color: 'text-indigo-500 bg-indigo-50 dark:bg-indigo-900/30', label: 'Workflow' },
  execution: { icon: Play, color: 'text-blue-500 bg-blue-50 dark:bg-blue-900/30', label: 'Execution' },
  agent: { icon: Server, color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30', label: 'Agent' },
  template: { icon: BookOpen, color: 'text-violet-500 bg-violet-50 dark:bg-violet-900/30', label: 'Template' },
  user: { icon: Users, color: 'text-amber-500 bg-amber-50 dark:bg-amber-900/30', label: 'User' },
};

/* ─── Search logic ─── */

async function performSearch(query: string): Promise<SearchResult[]> {
  if (!query || query.length < 2) return [];

  const results: SearchResult[] = [];

  try {
    const [wfRes, exRes, agRes] = await Promise.allSettled([
      client.get('/workflows/', { params: { per_page: 5 } }),
      client.get('/executions/', { params: { per_page: 5 } }),
      client.get('/agents', { params: { per_page: 5, search: query } }),
    ]);

    // Filter workflows client-side (API may not have search param)
    if (wfRes.status === 'fulfilled' && wfRes.value.data?.workflows) {
      const q = query.toLowerCase();
      wfRes.value.data.workflows
        .filter((w: any) => w.name?.toLowerCase().includes(q) || w.description?.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((w: any) => {
          results.push({
            id: w.id,
            type: 'workflow',
            title: w.name,
            subtitle: w.status,
            url: `/workflows/${w.id}/edit`,
          });
        });
    }

    // Filter executions
    if (exRes.status === 'fulfilled' && exRes.value.data?.executions) {
      const q = query.toLowerCase();
      exRes.value.data.executions
        .filter((e: any) => e.id?.toLowerCase().includes(q) || e.status?.toLowerCase().includes(q))
        .slice(0, 3)
        .forEach((e: any) => {
          results.push({
            id: e.id,
            type: 'execution',
            title: `Execution ${e.id.slice(0, 8)}`,
            subtitle: e.status,
            url: '/executions',
          });
        });
    }

    // Agents already filtered by search param
    if (agRes.status === 'fulfilled' && agRes.value.data?.agents) {
      agRes.value.data.agents.slice(0, 3).forEach((a: any) => {
        results.push({
          id: a.id,
          type: 'agent',
          title: a.name,
          subtitle: a.status,
          url: '/agents',
        });
      });
    }
  } catch {
    // Graceful: return what we have
  }

  return results;
}

/* ─── Component ─── */

export default function GlobalSearch({ onClose }: GlobalSearchProps) {
  const { t } = useLocale();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Keyboard shortcut: Escape to close, Cmd/Ctrl+K to toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // Auto-focus input on mount
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  // Debounced search
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
    setSelectedIndex(0);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.length < 2) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      const res = await performSearch(value);
      setResults(res);
      setLoading(false);
    }, 300);
  }, []);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault();
      navigate(results[selectedIndex].url);
      onClose();
    }
  };

  const handleSelect = (result: SearchResult) => {
    navigate(result.url);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="absolute top-[15%] left-1/2 -translate-x-1/2 w-full max-w-lg">
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
            <Search className="w-5 h-5 text-slate-400 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('search.placeholder')}
              className="flex-1 bg-transparent text-sm text-slate-900 dark:text-white outline-none placeholder:text-slate-400"
            />
            {loading && <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />}
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto">
            {results.length === 0 && query.length >= 2 && !loading && (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-slate-400">{t('common.noResults')}</p>
              </div>
            )}

            {results.length === 0 && query.length < 2 && (
              <div className="px-4 py-6 text-center space-y-2">
                <p className="text-sm text-slate-400">{t('search.hint')}</p>
                <div className="flex items-center justify-center gap-1 text-xs text-slate-400">
                  <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono">
                    <Command className="w-3 h-3 inline" />K
                  </kbd>
                  <span>{t('search.shortcutHint')}</span>
                </div>
              </div>
            )}

            {results.map((result, i) => {
              const cfg = TYPE_CONFIG[result.type] || TYPE_CONFIG.workflow;
              const Icon = cfg.icon;
              return (
                <button
                  key={`${result.type}-${result.id}`}
                  onClick={() => handleSelect(result)}
                  className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                    i === selectedIndex
                      ? 'bg-indigo-50 dark:bg-indigo-900/20'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{result.title}</p>
                    <p className="text-xs text-slate-400 truncate">
                      {cfg.label}
                      {result.subtitle && ` · ${result.subtitle}`}
                    </p>
                  </div>
                  <FileText className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" />
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-700 flex items-center gap-4 text-[10px] text-slate-400">
            <span><kbd className="px-1 bg-slate-100 dark:bg-slate-700 rounded font-mono">↑↓</kbd> navigate</span>
            <span><kbd className="px-1 bg-slate-100 dark:bg-slate-700 rounded font-mono">↵</kbd> select</span>
            <span><kbd className="px-1 bg-slate-100 dark:bg-slate-700 rounded font-mono">esc</kbd> close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
