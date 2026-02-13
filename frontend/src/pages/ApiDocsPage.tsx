import { useEffect, useState } from 'react';
import {
  FileText,
  ExternalLink,
  Search,
  ChevronDown,
  ChevronRight,
  Copy,
  CheckCircle2,
} from 'lucide-react';

/* ─── Types ─── */
interface EndpointInfo {
  method: string;
  path: string;
  summary: string;
  tag: string;
  auth: boolean;
}

/* ─── Method Badge ─── */
function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'bg-emerald-100 text-emerald-700',
    POST: 'bg-blue-100 text-blue-700',
    PUT: 'bg-amber-100 text-amber-700',
    PATCH: 'bg-orange-100 text-orange-700',
    DELETE: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`inline-block px-2 py-0.5 text-[10px] font-bold rounded font-mono ${colors[method] || 'bg-slate-100 text-slate-600'}`}>
      {method}
    </span>
  );
}

/* ─── Static endpoint catalog ─── */
const ENDPOINTS: EndpointInfo[] = [
  // Auth
  { method: 'POST', path: '/api/v1/auth/register', summary: 'Register new user + organization', tag: 'Auth', auth: false },
  { method: 'POST', path: '/api/v1/auth/login', summary: 'Login with email/password', tag: 'Auth', auth: false },
  { method: 'POST', path: '/api/v1/auth/refresh', summary: 'Refresh access token', tag: 'Auth', auth: false },
  { method: 'GET', path: '/api/v1/auth/me', summary: 'Get current user profile', tag: 'Auth', auth: true },
  // Users
  { method: 'GET', path: '/api/v1/users', summary: 'List users in organization', tag: 'Users', auth: true },
  { method: 'GET', path: '/api/v1/users/{id}', summary: 'Get user by ID', tag: 'Users', auth: true },
  { method: 'PUT', path: '/api/v1/users/{id}', summary: 'Update user profile', tag: 'Users', auth: true },
  { method: 'DELETE', path: '/api/v1/users/{id}', summary: 'Deactivate user', tag: 'Users', auth: true },
  // Workflows
  { method: 'GET', path: '/api/v1/workflows', summary: 'List workflows (paginated)', tag: 'Workflows', auth: true },
  { method: 'POST', path: '/api/v1/workflows', summary: 'Create new workflow', tag: 'Workflows', auth: true },
  { method: 'GET', path: '/api/v1/workflows/{id}', summary: 'Get workflow by ID', tag: 'Workflows', auth: true },
  { method: 'PUT', path: '/api/v1/workflows/{id}', summary: 'Update workflow definition', tag: 'Workflows', auth: true },
  { method: 'DELETE', path: '/api/v1/workflows/{id}', summary: 'Delete workflow (soft)', tag: 'Workflows', auth: true },
  { method: 'POST', path: '/api/v1/workflows/{id}/publish', summary: 'Publish workflow', tag: 'Workflows', auth: true },
  { method: 'POST', path: '/api/v1/workflows/{id}/archive', summary: 'Archive workflow', tag: 'Workflows', auth: true },
  { method: 'POST', path: '/api/v1/workflows/{id}/execute', summary: 'Execute workflow', tag: 'Workflows', auth: true },
  { method: 'POST', path: '/api/v1/workflows/{id}/clone', summary: 'Clone workflow', tag: 'Workflows', auth: true },
  { method: 'GET', path: '/api/v1/workflows/{id}/history', summary: 'Get workflow version history', tag: 'Workflows', auth: true },
  // Executions
  { method: 'GET', path: '/api/v1/executions', summary: 'List executions (paginated, filterable)', tag: 'Executions', auth: true },
  { method: 'GET', path: '/api/v1/executions/{id}', summary: 'Get execution details', tag: 'Executions', auth: true },
  { method: 'GET', path: '/api/v1/executions/{id}/logs', summary: 'Get execution logs', tag: 'Executions', auth: true },
  { method: 'POST', path: '/api/v1/executions/{id}/retry', summary: 'Retry failed execution', tag: 'Executions', auth: true },
  { method: 'POST', path: '/api/v1/executions/{id}/cancel', summary: 'Cancel running execution', tag: 'Executions', auth: true },
  // Agents
  { method: 'GET', path: '/api/v1/agents', summary: 'List agents (paginated)', tag: 'Agents', auth: true },
  { method: 'POST', path: '/api/v1/agents', summary: 'Register new agent', tag: 'Agents', auth: true },
  { method: 'GET', path: '/api/v1/agents/stats', summary: 'Get agent statistics', tag: 'Agents', auth: true },
  { method: 'POST', path: '/api/v1/agents/{id}/heartbeat', summary: 'Agent heartbeat', tag: 'Agents', auth: true },
  { method: 'POST', path: '/api/v1/agents/{id}/rotate-token', summary: 'Rotate agent token', tag: 'Agents', auth: true },
  // Credentials
  { method: 'GET', path: '/api/v1/credentials', summary: 'List credentials (values hidden)', tag: 'Credentials', auth: true },
  { method: 'POST', path: '/api/v1/credentials', summary: 'Create credential (AES-256 encrypted)', tag: 'Credentials', auth: true },
  { method: 'GET', path: '/api/v1/credentials/{id}', summary: 'Get credential (optional decrypt)', tag: 'Credentials', auth: true },
  { method: 'DELETE', path: '/api/v1/credentials/{id}', summary: 'Delete credential', tag: 'Credentials', auth: true },
  // Schedules
  { method: 'GET', path: '/api/v1/schedules', summary: 'List schedules', tag: 'Schedules', auth: true },
  { method: 'POST', path: '/api/v1/schedules', summary: 'Create schedule (cron)', tag: 'Schedules', auth: true },
  { method: 'POST', path: '/api/v1/schedules/{id}/toggle', summary: 'Enable/disable schedule', tag: 'Schedules', auth: true },
  // Templates
  { method: 'GET', path: '/api/v1/templates', summary: 'List workflow templates', tag: 'Templates', auth: true },
  { method: 'GET', path: '/api/v1/templates/{id}', summary: 'Get template details', tag: 'Templates', auth: true },
  { method: 'POST', path: '/api/v1/templates/{id}/instantiate', summary: 'Create workflow from template', tag: 'Templates', auth: true },
  // Triggers
  { method: 'GET', path: '/api/v1/triggers', summary: 'List triggers', tag: 'Triggers', auth: true },
  { method: 'POST', path: '/api/v1/triggers', summary: 'Create trigger', tag: 'Triggers', auth: true },
  { method: 'POST', path: '/api/v1/triggers/{id}/toggle', summary: 'Enable/disable trigger', tag: 'Triggers', auth: true },
  { method: 'POST', path: '/api/v1/triggers/{id}/fire', summary: 'Manually fire trigger', tag: 'Triggers', auth: true },
  // Analytics & Dashboard
  { method: 'GET', path: '/api/v1/dashboard/stats', summary: 'Dashboard statistics', tag: 'Analytics', auth: true },
  { method: 'GET', path: '/api/v1/analytics/overview', summary: 'Analytics overview', tag: 'Analytics', auth: true },
  { method: 'GET', path: '/api/v1/analytics/executions/timeline', summary: 'Execution timeline', tag: 'Analytics', auth: true },
  { method: 'GET', path: '/api/v1/analytics/workflows/performance', summary: 'Workflow performance metrics', tag: 'Analytics', auth: true },
  // Admin
  { method: 'GET', path: '/api/v1/admin/overview', summary: 'Admin overview (RBAC: admin.*)', tag: 'Admin', auth: true },
  { method: 'GET', path: '/api/v1/admin/roles', summary: 'List roles', tag: 'Admin', auth: true },
  { method: 'POST', path: '/api/v1/admin/roles', summary: 'Create role', tag: 'Admin', auth: true },
  { method: 'DELETE', path: '/api/v1/admin/roles/{id}', summary: 'Delete role', tag: 'Admin', auth: true },
  // Audit
  { method: 'GET', path: '/api/v1/audit-logs', summary: 'List audit logs (filterable)', tag: 'Audit', auth: true },
  { method: 'GET', path: '/api/v1/audit-logs/stats', summary: 'Audit log statistics', tag: 'Audit', auth: true },
  // Plugins
  { method: 'GET', path: '/api/v1/plugins', summary: 'List plugins', tag: 'Plugins', auth: true },
  { method: 'PUT', path: '/api/v1/plugins/{name}', summary: 'Enable/disable plugin', tag: 'Plugins', auth: true },
  { method: 'POST', path: '/api/v1/plugins/reload', summary: 'Reload all plugins', tag: 'Plugins', auth: true },
  // Export
  { method: 'GET', path: '/api/v1/export/executions', summary: 'Export executions (CSV/JSON)', tag: 'Export', auth: true },
  { method: 'GET', path: '/api/v1/export/audit-logs', summary: 'Export audit logs (CSV/JSON)', tag: 'Export', auth: true },
  { method: 'GET', path: '/api/v1/export/analytics', summary: 'Export analytics (CSV/JSON)', tag: 'Export', auth: true },
  // Bulk
  { method: 'POST', path: '/api/v1/bulk/workflows/publish', summary: 'Bulk publish workflows', tag: 'Bulk', auth: true },
  { method: 'POST', path: '/api/v1/bulk/workflows/archive', summary: 'Bulk archive workflows', tag: 'Bulk', auth: true },
  { method: 'POST', path: '/api/v1/bulk/workflows/delete', summary: 'Bulk delete workflows', tag: 'Bulk', auth: true },
  { method: 'POST', path: '/api/v1/bulk/executions/cancel', summary: 'Bulk cancel executions', tag: 'Bulk', auth: true },
  { method: 'POST', path: '/api/v1/bulk/executions/retry', summary: 'Bulk retry executions', tag: 'Bulk', auth: true },
  // Health & Metrics
  { method: 'GET', path: '/api/v1/health/', summary: 'Liveness probe', tag: 'Health', auth: false },
  { method: 'GET', path: '/api/v1/health/health', summary: 'Deep health check (DB + Redis)', tag: 'Health', auth: false },
  { method: 'GET', path: '/api/v1/health/status', summary: 'System status (uptime, versions)', tag: 'Health', auth: false },
  { method: 'GET', path: '/metrics', summary: 'Prometheus metrics', tag: 'Health', auth: false },
  // WebSocket
  { method: 'GET', path: '/ws', summary: 'WebSocket (JWT via query param)', tag: 'WebSocket', auth: true },
  // AI
  { method: 'POST', path: '/api/v1/ai/ask', summary: 'Ask Claude AI', tag: 'AI', auth: true },
  { method: 'POST', path: '/api/v1/ai/analyze', summary: 'AI data analysis', tag: 'AI', auth: true },
  { method: 'GET', path: '/api/v1/ai/usage', summary: 'AI usage statistics', tag: 'AI', auth: true },
];

/* ─── Main Page ─── */
export default function ApiDocsPage() {
  const [search, setSearch] = useState('');
  const [expandedTags, setExpandedTags] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<string | null>(null);

  const tags = [...new Set(ENDPOINTS.map((e) => e.tag))];

  const filtered = ENDPOINTS.filter((e) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      e.path.toLowerCase().includes(q) ||
      e.summary.toLowerCase().includes(q) ||
      e.method.toLowerCase().includes(q) ||
      e.tag.toLowerCase().includes(q)
    );
  });

  const toggleTag = (tag: string) => {
    setExpandedTags((prev) => {
      const next = new Set(prev);
      next.has(tag) ? next.delete(tag) : next.add(tag);
      return next;
    });
  };

  const expandAll = () => setExpandedTags(new Set(tags));
  const collapseAll = () => setExpandedTags(new Set());

  const copyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopied(path);
    setTimeout(() => setCopied(null), 2000);
  };

  const groupedByTag: Record<string, EndpointInfo[]> = {};
  for (const ep of filtered) {
    if (!groupedByTag[ep.tag]) groupedByTag[ep.tag] = [];
    groupedByTag[ep.tag].push(ep);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-500" />
            API Documentation
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {ENDPOINTS.length} endpoints across {tags.length} groups
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/api/v1/health/"
            target="_blank"
            rel="noopener"
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Live API
          </a>
          <button onClick={expandAll} className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 transition">
            Expand All
          </button>
          <button onClick={collapseAll} className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 transition">
            Collapse
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search endpoints..."
          className="w-full pl-9 pr-4 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Endpoint Groups */}
      <div className="space-y-3">
        {Object.entries(groupedByTag).map(([tag, endpoints]) => (
          <div key={tag} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <button
              onClick={() => toggleTag(tag)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition"
            >
              <div className="flex items-center gap-2">
                {expandedTags.has(tag) ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{tag}</span>
                <span className="text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded-full">
                  {endpoints.length}
                </span>
              </div>
            </button>

            {expandedTags.has(tag) && (
              <div className="border-t border-slate-100 dark:border-slate-700 divide-y divide-slate-50 dark:divide-slate-700/50">
                {endpoints.map((ep) => (
                  <div key={`${ep.method}-${ep.path}`} className="px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50/50 dark:hover:bg-slate-700/30">
                    <MethodBadge method={ep.method} />
                    <code className="text-xs font-mono text-slate-600 dark:text-slate-300 flex-1">{ep.path}</code>
                    <span className="text-xs text-slate-400 hidden md:block">{ep.summary}</span>
                    {!ep.auth && (
                      <span className="text-[9px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">public</span>
                    )}
                    <button
                      onClick={() => copyPath(ep.path)}
                      className="p-1 text-slate-300 hover:text-slate-500 transition"
                      title="Copy path"
                    >
                      {copied === ep.path ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-sm text-slate-400">
          No endpoints match your search
        </div>
      )}
    </div>
  );
}
