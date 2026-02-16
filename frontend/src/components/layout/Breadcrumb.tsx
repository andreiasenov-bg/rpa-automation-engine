import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { useEffect, useState } from 'react';
import { workflowApi } from '@/api/workflows';

const ROUTE_LABELS: Record<string, string> = {
  '': 'Dashboard',
  workflows: 'Workflows',
  executions: 'Executions',
  triggers: 'Triggers',
  schedules: 'Schedules',
  credentials: 'Credentials',
  users: 'Users',
  settings: 'Settings',
  templates: 'Templates',
  create: 'AI Creator',
  agents: 'Agents',
  notifications: 'Notifications',
  'audit-log': 'Audit Log',
  admin: 'Admin',
  plugins: 'Plugins',
  integrations: 'Integrations',
  'api-docs': 'API Docs',
  edit: 'Editor',
  files: 'Dashboard',
};

export default function Breadcrumb() {
  const location = useLocation();
  const [workflowName, setWorkflowName] = useState<string | null>(null);

  const segments = location.pathname.split('/').filter(Boolean);

  useEffect(() => {
    if (segments[0] === 'workflows' && segments[1] && !/^new/.test(segments[1])) {
      workflowApi
        .get(segments[1])
        .then((wf: any) => setWorkflowName(wf.name))
        .catch(() => setWorkflowName(null));
    } else {
      setWorkflowName(null);
    }
  }, [location.pathname]);

  const crumbs: { label: string; path: string }[] = [];

  segments.forEach((seg, i) => {
    const path = '/' + segments.slice(0, i + 1).join('/');
    if (/^[0-9a-f]{8}-/.test(seg)) {
      if (workflowName) {
        const short = workflowName.length > 42 ? workflowName.substring(0, 39) + '...' : workflowName;
        crumbs.push({ label: short, path: '/workflows/' + seg + '/files' });
      }
      return;
    }
    crumbs.push({ label: ROUTE_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1), path });
  });

  if (crumbs.length === 0) return null;

  return (
    <nav className="flex items-center gap-1.5 text-sm mb-4 px-1">
      <Link to="/" className="flex items-center gap-1 text-slate-400 hover:text-indigo-600 transition-colors">
        <Home size={14} />
      </Link>
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <span key={crumb.path + i} className="flex items-center gap-1.5">
            <ChevronRight size={12} className="text-slate-300" />
            {isLast ? (
              <span className="font-medium text-slate-700 dark:text-slate-200">{crumb.label}</span>
            ) : (
              <Link to={crumb.path} className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                {crumb.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
