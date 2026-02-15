import { useEffect, useState, useCallback } from 'react';
import {
  Plus,
  Search,
  Globe,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  ExternalLink,
  Trash2,
  Power,
  Activity,
  Clock,
  RefreshCw,
  Database,
  Code2,
  Radio,
  X,
  ChevronDown,
} from 'lucide-react';
import { integrationsApi, type Integration, type IntegrationCreate } from '@/api/integrations';

/* ─── Health badge ───────────────────────────────────────── */
function HealthBadge({ status }: { status?: string }) {
  if (!status) return null;
  const styles: Record<string, { color: string; label: string; icon: React.ElementType }> = {
    healthy: { color: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800', label: 'Healthy', icon: CheckCircle2 },
    degraded: { color: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800', label: 'Degraded', icon: AlertTriangle },
    unhealthy: { color: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800', label: 'Unhealthy', icon: XCircle },
    disabled: { color: 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600', label: 'Disabled', icon: Power },
    unknown: { color: 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600', label: 'Unknown', icon: Activity },
  };
  const s = styles[status] || styles.unknown;
  const Icon = s.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${s.color}`}>
      <Icon size={10} /> {s.label}
    </span>
  );
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  rest_api: Globe, graphql: Code2, websocket: Radio, database: Database,
};

const TYPES = [
  { value: 'rest_api', label: 'REST API' },
  { value: 'graphql', label: 'GraphQL' },
  { value: 'websocket', label: 'WebSocket' },
  { value: 'database', label: 'Database' },
  { value: 'soap', label: 'SOAP' },
  { value: 'grpc', label: 'gRPC' },
];

const AUTH_TYPES = [
  { value: 'none', label: 'No Auth' },
  { value: 'api_key', label: 'API Key' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
  { value: 'oauth2', label: 'OAuth 2.0' },
];

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Create form state
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState('rest_api');
  const [formUrl, setFormUrl] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formAuth, setFormAuth] = useState('none');
  const [formHealthUrl, setFormHealthUrl] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await integrationsApi.list();
      setIntegrations(Array.isArray(data) ? data : []);
    } catch {
      setIntegrations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchIntegrations(); }, [fetchIntegrations]);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const handleCreate = async () => {
    if (!formName.trim() || !formUrl.trim()) return;
    setCreating(true);
    try {
      await integrationsApi.create({
        name: formName.trim(),
        integration_type: formType,
        base_url: formUrl.trim(),
        description: formDesc.trim(),
        auth_type: formAuth,
        health_check_url: formHealthUrl.trim() || undefined,
        enabled: true,
      });
      setToast({ type: 'success', message: `Integration "${formName}" created!` });
      setShowCreate(false);
      setFormName(''); setFormType('rest_api'); setFormUrl(''); setFormDesc(''); setFormAuth('none'); setFormHealthUrl('');
      fetchIntegrations();
    } catch (err: any) {
      setToast({ type: 'error', message: err?.response?.data?.detail || 'Failed to create integration' });
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const result = await integrationsApi.toggle(id);
      setToast({ type: 'success', message: result.message });
      fetchIntegrations();
    } catch {
      setToast({ type: 'error', message: 'Failed to toggle integration' });
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete integration "${name}"?`)) return;
    try {
      await integrationsApi.delete(id);
      setToast({ type: 'success', message: `"${name}" removed` });
      fetchIntegrations();
    } catch {
      setToast({ type: 'error', message: 'Failed to delete' });
    }
  };

  const handleHealthCheck = async (id: string) => {
    try {
      await integrationsApi.healthCheck(id);
      setToast({ type: 'success', message: 'Health check completed' });
      fetchIntegrations();
    } catch {
      setToast({ type: 'error', message: 'Health check failed' });
    }
  };

  const filtered = search
    ? integrations.filter(
        (i) =>
          i.name.toLowerCase().includes(search.toLowerCase()) ||
          i.description?.toLowerCase().includes(search.toLowerCase()) ||
          i.base_url.toLowerCase().includes(search.toLowerCase()),
      )
    : integrations;

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium ${
          toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Integrations</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Connect external APIs, databases, and services to use in your workflows
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          Add Integration
        </button>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search integrations..."
            className="w-full pl-9 pr-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-slate-900 dark:text-white"
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 px-5 py-16 text-center">
          <Globe className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            {search ? 'No integrations match your search' : 'No integrations configured'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
            Connect external APIs, databases, and services to use them as data sources in your workflows
          </p>
          {!search && (
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              Add Your First Integration
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((intg) => {
            const TypeIcon = TYPE_ICONS[intg.integration_type] || Globe;
            return (
              <div
                key={intg.id}
                className={`bg-white dark:bg-slate-800 rounded-xl border-2 ${
                  intg.enabled
                    ? 'border-slate-200 dark:border-slate-700'
                    : 'border-slate-100 dark:border-slate-800 opacity-60'
                } p-5 hover:shadow-md transition-all`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                      <TypeIcon className="w-5 h-5 text-slate-600 dark:text-slate-300" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white text-sm">{intg.name}</h3>
                      <p className="text-xs text-slate-400 dark:text-slate-500">{intg.integration_type.replace('_', ' ').toUpperCase()}</p>
                    </div>
                  </div>
                  <HealthBadge status={intg.status || intg.health_status || (intg.enabled ? 'unknown' : 'disabled')} />
                </div>

                {intg.description && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mb-3 line-clamp-2">{intg.description}</p>
                )}

                <div className="text-xs text-slate-500 dark:text-slate-400 mb-3 truncate flex items-center gap-1">
                  <ExternalLink size={10} />
                  {intg.base_url}
                </div>

                {/* Stats */}
                {(intg.total_requests || intg.avg_response_ms) && (
                  <div className="flex gap-4 text-xs text-slate-500 dark:text-slate-400 mb-3">
                    {intg.total_requests != null && (
                      <span className="flex items-center gap-1"><Activity size={10} /> {intg.total_requests} requests</span>
                    )}
                    {intg.avg_response_ms != null && (
                      <span className="flex items-center gap-1"><Clock size={10} /> {intg.avg_response_ms}ms avg</span>
                    )}
                  </div>
                )}

                {/* Tags */}
                {intg.tags && intg.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {intg.tags.map((tag) => (
                      <span key={tag} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded text-[10px]">{tag}</span>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                  <button
                    onClick={() => handleToggle(intg.id)}
                    className={`flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg transition ${
                      intg.enabled
                        ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 hover:bg-amber-100'
                        : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100'
                    }`}
                  >
                    <Power size={12} />
                    {intg.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    onClick={() => handleHealthCheck(intg.id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-600 transition"
                  >
                    <RefreshCw size={12} />
                    Check
                  </button>
                  <button
                    onClick={() => handleDelete(intg.id, intg.name)}
                    className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition ml-auto"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowCreate(false)} />
          <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Globe className="w-5 h-5 text-indigo-500" />
                Add Integration
              </h2>
              <button onClick={() => setShowCreate(false)} className="p-1 text-slate-400 hover:text-slate-600">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Name *</label>
                <input
                  value={formName} onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Shopify API"
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Type</label>
                <select
                  value={formType} onChange={(e) => setFormType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                >
                  {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Base URL *</label>
                <input
                  value={formUrl} onChange={(e) => setFormUrl(e.target.value)}
                  placeholder="https://api.example.com"
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Description</label>
                <input
                  value={formDesc} onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="What this integration connects to"
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Authentication</label>
                <select
                  value={formAuth} onChange={(e) => setFormAuth(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                >
                  {AUTH_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-200 mb-1">Health Check URL</label>
                <input
                  value={formHealthUrl} onChange={(e) => setFormHealthUrl(e.target.value)}
                  placeholder="/health or /api/status"
                  className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 outline-none"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition">
                Cancel
              </button>
              <button onClick={handleCreate} disabled={creating || !formName.trim() || !formUrl.trim()}
                className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
