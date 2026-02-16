import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
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
  Globe,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useLocale } from '@/i18n';

interface NavItem {
  to: string;
  icon: React.ElementType;
  i18nKey: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: '',
    items: [
      { to: '/', icon: LayoutDashboard, i18nKey: 'nav.dashboard' },
    ],
  },
  {
    label: 'AUTOMATION',
    items: [
      { to: '/workflows', icon: Bot, i18nKey: 'nav.rpaList' },
      { to: '/create', icon: Wand2, i18nKey: 'nav.aiCreator' },
      { to: '/templates', icon: BookOpen, i18nKey: 'nav.templates' },
    ],
  },
  {
    label: 'TRIGGERS & SCHEDULING',
    items: [
      { to: '/triggers', icon: Zap, i18nKey: 'nav.triggers' },
      { to: '/schedules', icon: CalendarClock, i18nKey: 'nav.schedules' },
    ],
  },
  {
    label: 'CONNECTIONS',
    items: [
      { to: '/integrations', icon: Globe, i18nKey: 'nav.integrations' },
      { to: '/credentials', icon: Key, i18nKey: 'nav.credentials' },
    ],
  },
  {
    label: 'ADMINISTRATION',
    items: [
      { to: '/users', icon: Users, i18nKey: 'nav.users' },
      { to: '/agents', icon: Server, i18nKey: 'nav.agents' },
      { to: '/audit-log', icon: Shield, i18nKey: 'nav.auditLog' },
      { to: '/notifications', icon: Bell, i18nKey: 'nav.notifications' },
      { to: '/plugins', icon: Puzzle, i18nKey: 'nav.plugins' },
      { to: '/api-docs', icon: FileText, i18nKey: 'nav.apiDocs' },
      { to: '/admin', icon: Wrench, i18nKey: 'nav.admin' },
      { to: '/settings', icon: Settings, i18nKey: 'nav.settings' },
    ],
  },
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
      <nav className="flex-1 px-3 py-3 overflow-y-auto">
        {navGroups.map((group, gi) => (
          <div key={gi} className={gi > 0 ? 'mt-4' : ''}>
            {group.label && (
              <div className="px-3 mb-1 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map(({ to, icon: Icon, i18nKey }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/20 text-indigo-300'
                        : 'hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">{t(i18nKey)}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* User section */}
      <div className="px-3 py-3 border-t border-slate-700/50">
        <div className="px-3 py-1.5 text-xs text-slate-500 truncate">
          {user?.email}
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          {t('nav.logout')}
        </button>
      </div>
    </aside>
  );
}
