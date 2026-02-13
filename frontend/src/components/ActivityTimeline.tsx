/**
 * Activity Timeline component.
 *
 * Displays a chronological feed of user/system actions across the platform.
 * Groups activities by date, with icons and color coding by action type.
 */

import { useEffect, useState } from 'react';
import {
  Activity,
  GitBranch,
  Play,
  CheckCircle2,
  XCircle,
  Ban,
  Server,
  Wifi,
  WifiOff,
  Key,
  CalendarClock,
  UserPlus,
  LogIn,
  Edit3,
  Globe,
  Archive,
  Trash2,
  Loader2,
} from 'lucide-react';
import client from '@/api/client';
import { useLocale } from '@/i18n';

/* ─── Types ─── */

interface ActivityEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_id: string;
  actor_name: string;
  description: string;
  icon: string;
  color: string;
  timestamp: string | null;
  metadata: Record<string, unknown> | null;
}

interface ActivityResponse {
  activities: ActivityEntry[];
  grouped: Record<string, ActivityEntry[]>;
  total: number;
  period_days: number;
}

/* ─── Icon map ─── */

const ICON_MAP: Record<string, React.ElementType> = {
  GitBranch,
  Edit3,
  Globe,
  Archive,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  Ban,
  Server,
  Wifi,
  WifiOff,
  LogIn,
  UserPlus,
  Key,
  CalendarClock,
  Activity,
};

const COLOR_MAP: Record<string, { dot: string; bg: string }> = {
  emerald: { dot: 'bg-emerald-500', bg: 'bg-emerald-50 text-emerald-700' },
  red: { dot: 'bg-red-500', bg: 'bg-red-50 text-red-700' },
  blue: { dot: 'bg-blue-500', bg: 'bg-blue-50 text-blue-700' },
  amber: { dot: 'bg-amber-500', bg: 'bg-amber-50 text-amber-700' },
  slate: { dot: 'bg-slate-400', bg: 'bg-slate-50 text-slate-600' },
};

/* ─── Helpers ─── */

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function formatDateHeader(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

/* ─── Activity Item ─── */

function ActivityItem({ entry }: { entry: ActivityEntry }) {
  const IconComponent = ICON_MAP[entry.icon] || Activity;
  const colors = COLOR_MAP[entry.color] || COLOR_MAP.slate;

  return (
    <div className="flex gap-3 py-3">
      {/* Icon */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${colors.bg}`}>
        <IconComponent className="w-3.5 h-3.5" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-900 dark:text-white">
          <span className="font-medium">{entry.actor_name}</span>
          {' '}{entry.description}
        </p>
        {entry.resource_id && (
          <p className="text-xs text-slate-400 mt-0.5 font-mono truncate">
            {entry.resource_type}: {entry.resource_id.slice(0, 8)}...
          </p>
        )}
      </div>

      {/* Time */}
      <span className="text-xs text-slate-400 flex-shrink-0 mt-0.5">
        {formatTimestamp(entry.timestamp)}
      </span>
    </div>
  );
}

/* ─── Main Component ─── */

export default function ActivityTimeline({
  days = 7,
  limit = 30,
}: {
  days?: number;
  limit?: number;
}) {
  const { t } = useLocale();
  const [data, setData] = useState<ActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await client.get('/activity', { params: { days, limit } });
        setData(res.data);
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [days, limit]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!data || !data.activities || data.activities.length === 0) {
    return (
      <div className="py-8 text-center">
        <Activity className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-400">{t('activity.noActivity')}</p>
      </div>
    );
  }

  // Sort date keys descending (newest first)
  const dateKeys = Object.keys(data.grouped || {}).sort((a, b) => b.localeCompare(a));

  return (
    <div className="space-y-6">
      {dateKeys.map((dateKey) => (
        <div key={dateKey}>
          {/* Date header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              {formatDateHeader(dateKey)}
            </span>
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700" />
            <span className="text-xs text-slate-400">
              {data.grouped?.[dateKey]?.length ?? 0}
            </span>
          </div>

          {/* Activities for this date */}
          <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {data.grouped[dateKey].map((entry) => (
              <ActivityItem key={entry.id} entry={entry} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
