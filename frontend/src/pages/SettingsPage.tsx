import { useState, useEffect } from 'react';
import {
  Settings,
  Building2,
  Key,
  Bell,
  Palette,
  Save,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { userApi } from '@/api/users';
import ThemeToggle from '@/components/ThemeToggle';
import LocaleToggle from '@/components/LocaleToggle';
import { useLocale } from '@/i18n';

/* ─── Tab navigation ─── */
const TAB_DEFS = [
  { id: 'profile', i18nKey: 'settings.profile', icon: Settings },
  { id: 'organization', i18nKey: 'settings.organization', icon: Building2 },
  { id: 'security', i18nKey: 'settings.security', icon: Key },
  { id: 'notifications', i18nKey: 'settings.notifications', icon: Bell },
  { id: 'appearance', i18nKey: 'settings.appearance', icon: Palette },
] as const;

type TabId = typeof TAB_DEFS[number]['id'];

/* ─── Profile tab ─── */
function ProfileTab() {
  const user = useAuthStore((s) => s.user);
  const loadUser = useAuthStore((s) => s.loadUser);
  const { t } = useLocale();
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name);
      setLastName(user.last_name);
    }
  }, [user]);

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setSaved(false);
    try {
      await userApi.update(user.id, { first_name: firstName, last_name: lastName });
      await loadUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // error
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-4">{t('settings.personalInfo')}</h3>
        <div className="grid grid-cols-2 gap-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('auth.firstName')}</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('auth.lastName')}</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      <div className="max-w-md">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('auth.email')}</label>
        <input
          type="email"
          value={user?.email || ''}
          disabled
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm bg-slate-50 text-slate-500"
        />
        <p className="text-xs text-slate-400 mt-1">{t('settings.emailReadonly')}</p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {t('common.save')}
        </button>
        {saved && (
          <span className="flex items-center gap-1 text-sm text-emerald-600">
            <CheckCircle2 className="w-4 h-4" />
            {t('settings.saved')}
          </span>
        )}
      </div>
    </div>
  );
}

/* ─── Placeholder tabs ─── */
function ComingSoonTab({ title }: { title: string }) {
  return (
    <div className="py-12 text-center">
      <Settings className="w-8 h-8 text-slate-300 mx-auto mb-3" />
      <p className="text-sm text-slate-500">{title} settings will be available in a future update.</p>
    </div>
  );
}

/* ─── Main page ─── */
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile');
  const { t } = useLocale();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('settings.title')}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('settings.subtitle')}</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar tabs */}
        <div className="w-48 flex-shrink-0 space-y-0.5">
          {TAB_DEFS.map(({ id, i18nKey, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              {t(i18nKey)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          {activeTab === 'profile' && <ProfileTab />}
          {activeTab === 'organization' && <ComingSoonTab title={t('settings.organization')} />}
          {activeTab === 'security' && <ComingSoonTab title={t('settings.security')} />}
          {activeTab === 'notifications' && <ComingSoonTab title={t('settings.notifications')} />}
          {activeTab === 'appearance' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-1">{t('settings.theme')}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{t('settings.themeDesc')}</p>
                <ThemeToggle />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-1">{t('settings.language')}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{t('settings.languageDesc')}</p>
                <LocaleToggle />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
