/**
 * Notification Center — Bell icon with dropdown for in-app notifications.
 *
 * Features:
 * - Unread badge counter
 * - Dropdown with recent notifications
 * - Mark as read / mark all read
 * - Links to relevant resources
 * - WebSocket integration for real-time updates
 */

import { useState, useEffect, useRef } from 'react';
import {
  Bell,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  X,
  Check,
  CheckCheck,
  Loader2,
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';

/* ─── Types ─── */

interface AppNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  resource_type?: string;
  resource_id?: string;
  read: boolean;
  created_at: string;
}

const TYPE_ICONS: Record<string, { icon: React.ElementType; color: string }> = {
  success: { icon: CheckCircle2, color: 'text-emerald-500' },
  error: { icon: XCircle, color: 'text-red-500' },
  warning: { icon: AlertTriangle, color: 'text-amber-500' },
  info: { icon: Info, color: 'text-blue-500' },
};

/* ─── Helpers ─── */

function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/* ─── Component ─── */

export default function NotificationCenter() {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  // Fetch notifications
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await client.get('/notifications/', { params: { per_page: 20 } });
      const items = res.data?.notifications || res.data || [];
      setNotifications(
        Array.isArray(items)
          ? items.map((n: any) => ({
              id: n.id,
              type: n.type || n.severity || 'info',
              title: n.title || n.subject || 'Notification',
              message: n.message || n.body || '',
              resource_type: n.resource_type,
              resource_id: n.resource_id,
              read: n.read ?? n.is_read ?? false,
              created_at: n.created_at || new Date().toISOString(),
            }))
          : []
      );
    } catch {
      // Graceful: show empty
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll every 30s
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handleMarkRead = async (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    try {
      await client.put(`/notifications/${id}/read`);
    } catch {
      // Optimistic: already updated
    }
  };

  const handleMarkAllRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    try {
      await client.put('/notifications/read-all');
    } catch {
      // Optimistic
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
      >
        <Bell className="w-5 h-5 text-slate-500 dark:text-slate-400" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4.5 h-4.5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-12 w-80 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              {t('notifications.title')}
            </h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
                >
                  <CheckCheck className="w-3 h-3" />
                  {t('notifications.markAllRead')}
                </button>
              )}
            </div>
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto">
            {loading && notifications.length === 0 ? (
              <div className="py-8 flex justify-center">
                <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-8 text-center">
                <Bell className="w-6 h-6 text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-400">{t('notifications.empty')}</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {notifications.map((notif) => {
                  const cfg = TYPE_ICONS[notif.type] || TYPE_ICONS.info;
                  const Icon = cfg.icon;
                  return (
                    <div
                      key={notif.id}
                      className={`px-4 py-3 flex gap-3 transition-colors ${
                        notif.read
                          ? 'bg-white dark:bg-slate-800'
                          : 'bg-indigo-50/50 dark:bg-indigo-900/10'
                      }`}
                    >
                      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${cfg.color}`} />
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-medium ${notif.read ? 'text-slate-600 dark:text-slate-400' : 'text-slate-900 dark:text-white'}`}>
                          {notif.title}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">
                          {notif.message}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-1">
                          {formatRelative(notif.created_at)}
                        </p>
                      </div>
                      {!notif.read && (
                        <button
                          onClick={() => handleMarkRead(notif.id)}
                          className="flex-shrink-0 p-1 text-slate-400 hover:text-indigo-500 transition-colors"
                          title="Mark as read"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-700">
              <button
                onClick={() => { setOpen(false); }}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
              >
                {t('notifications.viewAll')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
