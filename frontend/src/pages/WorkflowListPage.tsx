import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  Search,
  GitBranch,
  MoreHorizontal,
  Play,
  Archive,
  Trash2,
  Edit3,
  Globe,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import type { Workflow } from '@/types';
import { workflowApi } from '@/api/workflows';

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 border-slate-200',
    published: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    archived: 'bg-amber-50 text-amber-700 border-amber-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        styles[status] || styles.draft
      }`}
    >
      {status}
    </span>
  );
}

export default function WorkflowListPage() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const perPage = 20;

  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await workflowApi.list(page, perPage);
      setWorkflows(data.workflows || []);
      setTotal(data.total || 0);
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  const handleCreate = async () => {
    try {
      const wf = await workflowApi.create({
        name: 'Untitled Workflow',
        description: '',
        definition: { steps: [], variables: {} },
      });
      navigate(`/workflows/${wf.id}/edit`);
    } catch {
      // handle error
    }
  };

  const handlePublish = async (id: string) => {
    await workflowApi.publish(id);
    setActionMenu(null);
    fetchWorkflows();
  };

  const handleArchive = async (id: string) => {
    await workflowApi.archive(id);
    setActionMenu(null);
    fetchWorkflows();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    await workflowApi.delete(id);
    setActionMenu(null);
    fetchWorkflows();
  };

  const handleExecute = async (id: string) => {
    try {
      await workflowApi.execute(id);
      setActionMenu(null);
    } catch {
      // handle error
    }
  };

  const filteredWorkflows = search
    ? workflows.filter(
        (w) =>
          w.name.toLowerCase().includes(search.toLowerCase()) ||
          w.description?.toLowerCase().includes(search.toLowerCase()),
      )
    : workflows;

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Workflows</h1>
          <p className="text-sm text-slate-500 mt-1">
            {total} workflow{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          New Workflow
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
            placeholder="Search workflows..."
            className="w-full pl-9 pr-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        </div>
      ) : filteredWorkflows.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-16 text-center">
          <GitBranch className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500 mb-4">
            {search ? 'No workflows match your search' : 'No workflows yet'}
          </p>
          {!search && (
            <button
              onClick={handleCreate}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              Create your first workflow
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Version
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Steps
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Updated
                </th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredWorkflows.map((wf) => (
                <tr key={wf.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <Link
                      to={`/workflows/${wf.id}/edit`}
                      className="text-sm font-medium text-slate-900 hover:text-indigo-600 transition-colors"
                    >
                      {wf.name}
                    </Link>
                    {wf.description && (
                      <p className="text-xs text-slate-400 mt-0.5 truncate max-w-xs">
                        {wf.description}
                      </p>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={wf.status} />
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">v{wf.version}</td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {wf.definition?.steps?.length || 0}
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {new Date(wf.updated_at).toLocaleDateString()}
                  </td>
                  <td className="px-3 py-3.5 relative">
                    <button
                      onClick={() => setActionMenu(actionMenu === wf.id ? null : wf.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <MoreHorizontal className="w-4 h-4 text-slate-400" />
                    </button>

                    {actionMenu === wf.id && (
                      <div className="absolute right-3 top-12 z-20 w-44 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                        <Link
                          to={`/workflows/${wf.id}/edit`}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          Edit
                        </Link>
                        {wf.status === 'published' && (
                          <button
                            onClick={() => handleExecute(wf.id)}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                          >
                            <Play className="w-3.5 h-3.5" />
                            Execute
                          </button>
                        )}
                        {wf.status === 'draft' && (
                          <button
                            onClick={() => handlePublish(wf.id)}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                          >
                            <Globe className="w-3.5 h-3.5" />
                            Publish
                          </button>
                        )}
                        {wf.status !== 'archived' && (
                          <button
                            onClick={() => handleArchive(wf.id)}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                          >
                            <Archive className="w-3.5 h-3.5" />
                            Archive
                          </button>
                        )}
                        <hr className="my-1 border-slate-100" />
                        <button
                          onClick={() => handleDelete(wf.id)}
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Page {page} of {totalPages}
              </p>
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
    </div>
  );
}
