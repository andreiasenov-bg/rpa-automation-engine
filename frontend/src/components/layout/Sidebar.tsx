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
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/workflows', icon: GitBranch, label: 'Workflows' },
  { to: '/executions', icon: Play, label: 'Executions' },
  { to: '/templates', icon: BookOpen, label: 'Templates' },
  { to: '/triggers', icon: Zap, label: 'Triggers' },
  { to: '/schedules', icon: CalendarClock, label: 'Schedules' },
  { to: '/credentials', icon: Key, label: 'Credentials' },
  { to: '/agents', icon: Server, label: 'Agents' },
  { to: '/users', icon: Users, label: 'Users' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/audit-log', icon: Shield, label: 'Audit Log' },
  { to: '/admin', icon: Wrench, label: 'Admin' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-60 min-h-screen bg-slate-900 text-slate-300 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-2 border-b border-slate-700/50">
        <Bot className="w-7 h-7 text-indigo-400" />
        <span className="text-lg font-bold text-white tracking-tight">RPA Engine</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
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
            {label}
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
          Log out
        </button>
      </div>
    </aside>
  );
}
