import { useEffect, useState, useCallback } from 'react';
import {
  Puzzle,
  Loader2,
  RefreshCw,
  Power,
  PowerOff,
  AlertCircle,
  Package,
  ExternalLink,
  FolderOpen,
  Tag,
} from 'lucide-react';
import { pluginsApi, type PluginInfo } from '@/api/plugins';

/* ─── Source Badge ─── */
function SourceBadge({ source }: { source: string }) {
  const styles: Record<string, string> = {
    builtin: 'bg-blue-50 text-blue-700',
    entrypoint: 'bg-violet-50 text-violet-700',
    local: 'bg-emerald-50 text-emerald-700',
  };
  const icons: Record<string, React.ElementType> = {
    builtin: Package,
    entrypoint: ExternalLink,
    local: FolderOpen,
  };
  const Icon = icons[source] || Package;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full ${styles[source] || 'bg-slate-100 text-slate-600'}`}>
      <Icon className="w-3 h-3" />
      {source}
    </span>
  );
}

/* ─── Plugin Card ─── */
function PluginCard({
  plugin,
  onToggle,
}: {
  plugin: PluginInfo;
  onToggle: (name: string, enabled: boolean) => void;
}) {
  const hasErrors = plugin.errors.length > 0;

  return (
    <div className={`bg-white rounded-xl border ${hasErrors ? 'border-red-200' : 'border-slate-200'} p-5 transition hover:shadow-sm`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Puzzle className={`w-5 h-5 ${plugin.enabled ? 'text-indigo-500' : 'text-slate-300'}`} />
          <div>
            <h3 className="text-sm font-semibold text-slate-900">{plugin.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <SourceBadge source={plugin.source} />
              {plugin.version !== '0.0.0' && (
                <span className="text-[10px] text-slate-400">v{plugin.version}</span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => onToggle(plugin.name, !plugin.enabled)}
          className={`p-1.5 rounded-lg transition ${
            plugin.enabled
              ? 'text-emerald-600 hover:bg-emerald-50'
              : 'text-slate-400 hover:bg-slate-100'
          }`}
          title={plugin.enabled ? 'Disable' : 'Enable'}
        >
          {plugin.enabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
        </button>
      </div>

      {plugin.description && (
        <p className="text-xs text-slate-500 mb-3">{plugin.description}</p>
      )}

      {plugin.task_types.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {plugin.task_types.map((t) => (
            <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono bg-slate-50 text-slate-600 rounded">
              <Tag className="w-2.5 h-2.5" />
              {t}
            </span>
          ))}
        </div>
      )}

      {hasErrors && (
        <div className="bg-red-50 rounded-lg p-2 mt-2">
          <div className="flex items-center gap-1 text-xs text-red-600 font-medium mb-1">
            <AlertCircle className="w-3 h-3" /> Errors
          </div>
          {plugin.errors.map((err, i) => (
            <p key={i} className="text-[10px] text-red-500 font-mono">{err}</p>
          ))}
        </div>
      )}

      {plugin.author && (
        <p className="text-[10px] text-slate-400 mt-2">by {plugin.author}</p>
      )}
    </div>
  );
}

/* ─── Main Page ─── */
export default function PluginsPage() {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);

  const fetchPlugins = useCallback(async () => {
    setLoading(true);
    try {
      const data = await pluginsApi.list();
      setPlugins(data.plugins || []);
    } catch {
      // handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      await pluginsApi.toggle(name, enabled);
      setPlugins((prev) =>
        prev.map((p) => (p.name === name ? { ...p, enabled } : p)),
      );
    } catch {
      // handle
    }
  };

  const handleReload = async () => {
    setReloading(true);
    try {
      await pluginsApi.reload();
      await fetchPlugins();
    } catch {
      // handle
    } finally {
      setReloading(false);
    }
  };

  const enabledCount = plugins.filter((p) => p.enabled).length;
  const errorCount = plugins.filter((p) => p.errors.length > 0).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Puzzle className="w-6 h-6 text-indigo-500" />
            Plugins
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {plugins.length} plugin{plugins.length !== 1 ? 's' : ''} &middot;{' '}
            {enabledCount} enabled
            {errorCount > 0 && (
              <span className="text-red-500"> &middot; {errorCount} with errors</span>
            )}
          </p>
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${reloading ? 'animate-spin' : ''}`} />
          Reload
        </button>
      </div>

      {plugins.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Puzzle className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-2">No plugins discovered</p>
          <p className="text-xs text-slate-400">
            Place plugin modules in <code className="bg-slate-100 px-1 rounded">plugins/</code> or
            install packages with <code className="bg-slate-100 px-1 rounded">rpa_engine.tasks</code> entry points.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {plugins.map((plugin) => (
            <PluginCard
              key={plugin.name}
              plugin={plugin}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}
