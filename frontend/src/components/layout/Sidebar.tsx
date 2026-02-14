import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  Play,
  Zap,
  CalendarClock,
  Key,
  Users,
  Settings,
  LogOut,
  Bot,
  Shield,
  BookOpen,
  Server,
  Bell,
  Wrench,
  Puzzle,
  FileText,
  Wand2,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useLocale } from '@/i18n';

const navItems = [
  { to: '/', icon: LayoutDashboard, i18nKey: 'nav.dashboard' },
  { to: '/workflows', icon: GitBranch, i18nKey: 'nav.workflows' },
  { to: '/executions', icon: Play, i18nKey: 'nav.executions' },
  { to: '/templates', icon: BookOpen, i18nKey: 'nav.templates' },
  { to: '/create', icon: Wand2, i18nKey: 'nav.aiCreator' },
  { to: '/triggers', icon: Zap, i18nKey: 'nav.triggers' },
  { to: '/schedules', icon: CalendarClock, i18nKey: 'nav.schedules' },
  { to: '/credentials', icon: Key, i18nKey: 'nav.credentials' },
  { to: '/agents', icon: Server, i18nKey: 'nav.agents' },
  { to: '/users', icon: Users, i18nKey: 'nav.users' },
  { to: '/notifications', icon: Bell, i18nKey: 'nav.notifications' },
  { to: '/audit-log', icon: Shield, i18nKey: 'nav.auditLog' },
  { to: '/plugins', icon: Puzzle, i18nKey: 'nav.plugins' },
  { to: '/api-docs', icon: FileText, i18nKey: 'nav.apiDocs' },
  { to: '/admin', icon: Wrench, i18nKey: 'nav.admin' },
  { to: '/settings', icon: Settings, i18nKey: 'nav.settings' },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const { t } = useLocale();

  return (
    <aside className="w-60 min-h-screen bg-slate-900 text-slate-300 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-2 border-b border-slate-700/50">
        <Bot className="w-7 h-7 text-indigo-400" />
        <span className="text-lg font-bold text-white tracking-tight">RPA Engine</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, i18nKey }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300'
                  : 'hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Icon className="w-4.5 h-4.5" />
            {t(i18nKey)}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="px-3 py-4 border-t border-slate-700/50">
        <div className="px-3 py-2 text-xs text-slate-500 truncate">
          {user?.email}
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4.5 h-4.5" />
          {t('nav.logout')}
        </button>
      </div>
    </aside>
  );
}
