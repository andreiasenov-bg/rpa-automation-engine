import { useEffect, useState, useCallback } from 'react';
import {
  Key,
  Plus,
  MoreHorizontal,
  Trash2,
  Eye,
  EyeOff,
  Copy,
  Loader2,
  Shield,
} from 'lucide-react';
import {
  listCredentials,
  createCredential,
  deleteCredential,
  getCredential,
  type Credential,
  type CredentialCreate,
} from '@/api/credentials';

/* ─── Type badge ─── */
const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  api_key: { label: 'API Key', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  oauth2: { label: 'OAuth 2.0', color: 'bg-purple-50 text-purple-700 border-purple-200' },
  basic_auth: { label: 'Basic Auth', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  database: { label: 'Database', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  private_key: { label: 'Private Key', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  custom: { label: 'Custom', color: 'bg-slate-50 text-slate-600 border-slate-200' },
};

function TypeBadge({ type }: { type: string }) {
  const cfg = TYPE_LABELS[type] || TYPE_LABELS.custom;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

/* ─── Create modal ─── */
function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [credType, setCredType] = useState('api_key');
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !value) return;
    setSaving(true);
    setError('');
    try {
      await createCredential({ name, credential_type: credType, value } as CredentialCreate);
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create credential');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-md space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">New Credential</h2>
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. GitHub Token"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
          <select
            value={credType}
            onChange={(e) => setCredType(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {Object.entries(TYPE_LABELS).map(([key, cfg]) => (
              <option key={key} value={key}>{cfg.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Value</label>
          <textarea
            required
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Paste credential value..."
          />
          <p className="text-xs text-slate-400 mt-1">Encrypted with AES-256 before storage</p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition">
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-50 flex items-center gap-1.5"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Create
          </button>
        </div>
      </form>
    </div>
  );
}

/* ─── Main page ─── */
export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [revealedValues, setRevealedValues] = useState<Record<string, string>>({});
  const perPage = 25;

  const fetchCredentials = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCredentials({ page, per_page: perPage, search: search || undefined });
      setCredentials(data.items || []);
      setTotal(data.total || 0);
    } catch {
      setCredentials([]);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  const handleReveal = async (id: string) => {
    if (revealedValues[id]) {
      // Toggle off
      setRevealedValues((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      return;
    }
    try {
      const cred = await getCredential(id, true);
      if (cred.value) {
        setRevealedValues((prev) => ({ ...prev, [id]: cred.value! }));
      }
    } catch {
      // error
    }
  };

  const handleCopy = (value: string) => {
    navigator.clipboard.writeText(value);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this credential? This cannot be undone.')) return;
    try {
      await deleteCredential(id);
      setActionMenu(null);
      fetchCredentials();
    } catch {
      // error
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Credentials</h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} credential{total !== 1 ? 's' : ''} in vault
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          New Credential
        </button>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search credentials..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="w-full max-w-sm px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : credentials.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <Shield className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">No credentials stored yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            Add your first credential
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Value</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Created</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {credentials.map((cred) => (
                <tr key={cred.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      <span className="text-sm font-medium text-slate-900">{cred.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5"><TypeBadge type={cred.credential_type} /></td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      {revealedValues[cred.id] ? (
                        <>
                          <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono max-w-xs truncate">
                            {revealedValues[cred.id]}
                          </code>
                          <button onClick={() => handleCopy(revealedValues[cred.id])} className="p-1 rounded hover:bg-slate-100" title="Copy">
                            <Copy className="w-3.5 h-3.5 text-slate-400" />
                          </button>
                        </>
                      ) : (
                        <span className="text-xs text-slate-400 font-mono">••••••••••••</span>
                      )}
                      <button onClick={() => handleReveal(cred.id)} className="p-1 rounded hover:bg-slate-100" title={revealedValues[cred.id] ? 'Hide' : 'Reveal'}>
                        {revealedValues[cred.id] ? (
                          <EyeOff className="w-3.5 h-3.5 text-slate-400" />
                        ) : (
                          <Eye className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {cred.created_at ? new Date(cred.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-3 py-3.5 relative">
                    <button
                      onClick={() => setActionMenu(actionMenu === cred.id ? null : cred.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </button>
                    {actionMenu === cred.id && (
                      <div className="absolute right-3 top-12 z-20 w-36 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                        <button
                          onClick={() => handleDelete(cred.id)}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 disabled:opacity-50 hover:bg-slate-50 transition"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onCreated={fetchCredentials} />
      )}
    </div>
  );
}
