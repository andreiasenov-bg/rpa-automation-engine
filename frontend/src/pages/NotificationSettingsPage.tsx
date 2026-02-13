import { useEffect, useState } from 'react';
import {
  Bell,
  Mail,
  MessageSquare,
  Webhook,
  Wifi,
  Save,
  Loader2,
  CheckCircle,
  TestTube,
} from 'lucide-react';
import client from '@/api/client';

/* ─── Types ─── */
interface ChannelConfig {
  enabled: boolean;
  config: Record<string, string>;
}

interface NotificationPreferences {
  email: ChannelConfig;
  slack: ChannelConfig;
  webhook: ChannelConfig;
  websocket: ChannelConfig;
  events: {
    execution_completed: boolean;
    execution_failed: boolean;
    execution_started: boolean;
    agent_disconnected: boolean;
    schedule_missed: boolean;
    credential_expiring: boolean;
  };
}

const DEFAULT_PREFS: NotificationPreferences = {
  email: { enabled: false, config: { smtp_host: '', smtp_port: '587', from_email: '', username: '', password: '' } },
  slack: { enabled: false, config: { webhook_url: '' } },
  webhook: { enabled: false, config: { url: '', secret: '' } },
  websocket: { enabled: true, config: {} },
  events: {
    execution_completed: true,
    execution_failed: true,
    execution_started: false,
    agent_disconnected: true,
    schedule_missed: true,
    credential_expiring: true,
  },
};

const EVENT_LABELS: Record<string, { label: string; description: string }> = {
  execution_completed: { label: 'Execution Completed', description: 'Notify when a workflow execution completes successfully' },
  execution_failed: { label: 'Execution Failed', description: 'Notify when a workflow execution fails' },
  execution_started: { label: 'Execution Started', description: 'Notify when a workflow execution begins' },
  agent_disconnected: { label: 'Agent Disconnected', description: 'Notify when an agent goes offline' },
  schedule_missed: { label: 'Schedule Missed', description: 'Notify when a scheduled execution was missed' },
  credential_expiring: { label: 'Credential Expiring', description: 'Notify when a stored credential is about to expire' },
};

/* ─── Channel config section ─── */
function ChannelSection({
  icon: Icon,
  title,
  description,
  channel,
  prefs,
  onChange,
  fields,
  onTest,
  testing,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  channel: keyof Pick<NotificationPreferences, 'email' | 'slack' | 'webhook' | 'websocket'>;
  prefs: NotificationPreferences;
  onChange: (p: NotificationPreferences) => void;
  fields: Array<{ key: string; label: string; type?: string; placeholder?: string }>;
  onTest: () => void;
  testing: boolean;
}) {
  const ch = prefs[channel];

  const toggleEnabled = () => {
    onChange({ ...prefs, [channel]: { ...ch, enabled: !ch.enabled } });
  };

  const setField = (key: string, val: string) => {
    onChange({ ...prefs, [channel]: { ...ch, config: { ...ch.config, [key]: val } } });
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${ch.enabled ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            <p className="text-xs text-slate-500">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {ch.enabled && (
            <button onClick={onTest} disabled={testing}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition disabled:opacity-50">
              {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <TestTube className="w-3 h-3" />}
              Test
            </button>
          )}
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={ch.enabled} onChange={toggleEnabled} className="sr-only peer" />
            <div className="w-9 h-5 bg-slate-200 peer-checked:bg-indigo-600 rounded-full transition-colors after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
          </label>
        </div>
      </div>

      {ch.enabled && fields.length > 0 && (
        <div className="mt-4 space-y-3 pl-12">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-slate-600 mb-1">{f.label}</label>
              <input
                type={f.type || 'text'}
                value={ch.config[f.key] || ''}
                onChange={(e) => setField(f.key, e.target.value)}
                placeholder={f.placeholder}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Main page ─── */
export default function NotificationSettingsPage() {
  const [prefs, setPrefs] = useState<NotificationPreferences>(DEFAULT_PREFS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testingChannel, setTestingChannel] = useState('');

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save channel configs to backend
      for (const channel of ['email', 'slack', 'webhook'] as const) {
        if (prefs[channel].enabled) {
          await client.post('/notifications/channels/configure', {
            channel,
            config: prefs[channel].config,
          });
        }
      }
      // Persist preferences to localStorage for now
      localStorage.setItem('notification_prefs', JSON.stringify(prefs));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (channel: string) => {
    setTestingChannel(channel);
    try {
      await client.post(`/notifications/test?channel=${channel}`);
    } catch {
      // handle
    } finally {
      setTestingChannel('');
    }
  };

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('notification_prefs');
    if (stored) {
      try {
        setPrefs(JSON.parse(stored));
      } catch {
        // ignore
      }
    }
  }, []);

  const toggleEvent = (key: string) => {
    setPrefs({
      ...prefs,
      events: { ...prefs.events, [key]: !prefs.events[key as keyof typeof prefs.events] },
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Bell className="w-6 h-6 text-indigo-500" />
            Notification Settings
          </h1>
          <p className="text-sm text-slate-500 mt-1">Configure how and when you receive notifications</p>
        </div>
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 transition">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* Channels */}
      <h2 className="text-sm font-semibold text-slate-700 mb-3">Notification Channels</h2>
      <div className="space-y-3 mb-8">
        <ChannelSection
          icon={Mail} title="Email" description="Send notifications via SMTP email"
          channel="email" prefs={prefs} onChange={setPrefs}
          onTest={() => handleTest('email')} testing={testingChannel === 'email'}
          fields={[
            { key: 'smtp_host', label: 'SMTP Host', placeholder: 'smtp.gmail.com' },
            { key: 'smtp_port', label: 'SMTP Port', placeholder: '587' },
            { key: 'from_email', label: 'From Email', placeholder: 'noreply@example.com' },
            { key: 'username', label: 'Username' },
            { key: 'password', label: 'Password', type: 'password' },
          ]}
        />
        <ChannelSection
          icon={MessageSquare} title="Slack" description="Send notifications to a Slack channel"
          channel="slack" prefs={prefs} onChange={setPrefs}
          onTest={() => handleTest('slack')} testing={testingChannel === 'slack'}
          fields={[
            { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/services/...' },
          ]}
        />
        <ChannelSection
          icon={Webhook} title="Webhook" description="POST notifications to a custom URL"
          channel="webhook" prefs={prefs} onChange={setPrefs}
          onTest={() => handleTest('webhook')} testing={testingChannel === 'webhook'}
          fields={[
            { key: 'url', label: 'Webhook URL', placeholder: 'https://your-api.com/webhooks/rpa' },
            { key: 'secret', label: 'Signing Secret (optional)', type: 'password' },
          ]}
        />
        <ChannelSection
          icon={Wifi} title="WebSocket" description="Real-time in-app notifications"
          channel="websocket" prefs={prefs} onChange={setPrefs}
          onTest={() => handleTest('websocket')} testing={testingChannel === 'websocket'}
          fields={[]}
        />
      </div>

      {/* Event subscriptions */}
      <h2 className="text-sm font-semibold text-slate-700 mb-3">Event Subscriptions</h2>
      <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
        {Object.entries(EVENT_LABELS).map(([key, { label, description }]) => (
          <div key={key} className="px-5 py-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">{label}</p>
              <p className="text-xs text-slate-500">{description}</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={prefs.events[key as keyof typeof prefs.events]}
                onChange={() => toggleEvent(key)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-200 peer-checked:bg-indigo-600 rounded-full transition-colors after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
