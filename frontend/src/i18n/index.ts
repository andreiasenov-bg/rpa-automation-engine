/**
 * Lightweight i18n system for RPA Engine.
 *
 * Usage:
 *   import { t, useLocale } from '@/i18n';
 *   const label = t('dashboard.title');  // "Dashboard" or "Табло"
 *
 *   // In a component:
 *   const { locale, setLocale, t } = useLocale();
 */

import { create } from 'zustand';

export type Locale = 'en' | 'bg';

type TranslationMap = Record<string, string>;

/* ─── Translation dictionaries ─── */

const translations: Record<Locale, TranslationMap> = {
  en: {
    // Common
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.create': 'Create',
    'common.edit': 'Edit',
    'common.search': 'Search',
    'common.loading': 'Loading...',
    'common.noResults': 'No results found',
    'common.confirm': 'Confirm',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.export': 'Export',
    'common.refresh': 'Refresh',
    'common.close': 'Close',
    'common.yes': 'Yes',
    'common.no': 'No',
    'common.all': 'All',
    'common.enabled': 'Enabled',
    'common.disabled': 'Disabled',
    'common.active': 'Active',
    'common.inactive': 'Inactive',

    // Navigation
    'nav.dashboard': 'Dashboard',
    'nav.workflows': 'Workflows',
    'nav.executions': 'Executions',
    'nav.templates': 'Templates',
    'nav.triggers': 'Triggers',
    'nav.schedules': 'Schedules',
    'nav.credentials': 'Credentials',
    'nav.agents': 'Agents',
    'nav.users': 'Users',
    'nav.notifications': 'Notifications',
    'nav.auditLog': 'Audit Log',
    'nav.plugins': 'Plugins',
    'nav.apiDocs': 'API Docs',
    'nav.admin': 'Admin',
    'nav.settings': 'Settings',
    'nav.logout': 'Log out',

    // Auth
    'auth.login': 'Log in',
    'auth.register': 'Register',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.confirmPassword': 'Confirm Password',
    'auth.firstName': 'First Name',
    'auth.lastName': 'Last Name',
    'auth.orgName': 'Organization Name',
    'auth.forgotPassword': 'Forgot password?',
    'auth.noAccount': "Don't have an account?",
    'auth.hasAccount': 'Already have an account?',

    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.totalWorkflows': 'Total Workflows',
    'dashboard.activeWorkflows': 'Active',
    'dashboard.totalExecutions': 'Total Executions',
    'dashboard.running': 'Running',
    'dashboard.completed': 'Completed',
    'dashboard.failed': 'Failed',
    'dashboard.recentExecutions': 'Recent Executions',

    // Workflows
    'workflows.title': 'Workflows',
    'workflows.new': 'New Workflow',
    'workflows.editor': 'Workflow Editor',
    'workflows.publish': 'Publish',
    'workflows.archive': 'Archive',
    'workflows.execute': 'Execute',
    'workflows.clone': 'Clone',
    'workflows.delete': 'Delete Workflow',

    // Executions
    'executions.title': 'Executions',
    'executions.retry': 'Retry',
    'executions.cancel': 'Cancel',
    'executions.logs': 'Logs',
    'executions.status.pending': 'Pending',
    'executions.status.running': 'Running',
    'executions.status.completed': 'Completed',
    'executions.status.failed': 'Failed',
    'executions.status.cancelled': 'Cancelled',

    // Settings
    'settings.title': 'Settings',
    'settings.profile': 'Profile',
    'settings.organization': 'Organization',
    'settings.security': 'Security',
    'settings.notifications': 'Notifications',
    'settings.appearance': 'Appearance',
    'settings.theme': 'Theme',
    'settings.themeDesc': 'Choose your preferred color scheme',
    'settings.light': 'Light',
    'settings.dark': 'Dark',
    'settings.system': 'System',

    // Admin
    'admin.title': 'Admin Panel',
    'admin.overview': 'Overview',
    'admin.roles': 'Roles',
    'admin.permissions': 'Permissions',
    'admin.createRole': 'New Role',
  },

  bg: {
    // Общи
    'common.save': 'Запази',
    'common.cancel': 'Отказ',
    'common.delete': 'Изтрий',
    'common.create': 'Създай',
    'common.edit': 'Редактирай',
    'common.search': 'Търсене',
    'common.loading': 'Зареждане...',
    'common.noResults': 'Няма резултати',
    'common.confirm': 'Потвърди',
    'common.back': 'Назад',
    'common.next': 'Напред',
    'common.export': 'Експорт',
    'common.refresh': 'Обнови',
    'common.close': 'Затвори',
    'common.yes': 'Да',
    'common.no': 'Не',
    'common.all': 'Всички',
    'common.enabled': 'Включено',
    'common.disabled': 'Изключено',
    'common.active': 'Активно',
    'common.inactive': 'Неактивно',

    // Навигация
    'nav.dashboard': 'Табло',
    'nav.workflows': 'Процеси',
    'nav.executions': 'Изпълнения',
    'nav.templates': 'Шаблони',
    'nav.triggers': 'Тригери',
    'nav.schedules': 'Разписания',
    'nav.credentials': 'Идентификации',
    'nav.agents': 'Агенти',
    'nav.users': 'Потребители',
    'nav.notifications': 'Известия',
    'nav.auditLog': 'Одит лог',
    'nav.plugins': 'Плъгини',
    'nav.apiDocs': 'API Документация',
    'nav.admin': 'Админ',
    'nav.settings': 'Настройки',
    'nav.logout': 'Изход',

    // Автентикация
    'auth.login': 'Вход',
    'auth.register': 'Регистрация',
    'auth.email': 'Имейл',
    'auth.password': 'Парола',
    'auth.confirmPassword': 'Потвърди парола',
    'auth.firstName': 'Име',
    'auth.lastName': 'Фамилия',
    'auth.orgName': 'Име на организация',
    'auth.forgotPassword': 'Забравена парола?',
    'auth.noAccount': 'Нямате акаунт?',
    'auth.hasAccount': 'Вече имате акаунт?',

    // Табло
    'dashboard.title': 'Табло',
    'dashboard.totalWorkflows': 'Общо процеси',
    'dashboard.activeWorkflows': 'Активни',
    'dashboard.totalExecutions': 'Общо изпълнения',
    'dashboard.running': 'Изпълняващи се',
    'dashboard.completed': 'Завършени',
    'dashboard.failed': 'Неуспешни',
    'dashboard.recentExecutions': 'Последни изпълнения',

    // Процеси
    'workflows.title': 'Процеси',
    'workflows.new': 'Нов процес',
    'workflows.editor': 'Редактор на процеси',
    'workflows.publish': 'Публикувай',
    'workflows.archive': 'Архивирай',
    'workflows.execute': 'Изпълни',
    'workflows.clone': 'Клонирай',
    'workflows.delete': 'Изтрий процес',

    // Изпълнения
    'executions.title': 'Изпълнения',
    'executions.retry': 'Повтори',
    'executions.cancel': 'Отмени',
    'executions.logs': 'Логове',
    'executions.status.pending': 'Чакащо',
    'executions.status.running': 'Изпълнява се',
    'executions.status.completed': 'Завършено',
    'executions.status.failed': 'Неуспешно',
    'executions.status.cancelled': 'Отменено',

    // Настройки
    'settings.title': 'Настройки',
    'settings.profile': 'Профил',
    'settings.organization': 'Организация',
    'settings.security': 'Сигурност',
    'settings.notifications': 'Известия',
    'settings.appearance': 'Външен вид',
    'settings.theme': 'Тема',
    'settings.themeDesc': 'Изберете предпочитаната цветова схема',
    'settings.light': 'Светла',
    'settings.dark': 'Тъмна',
    'settings.system': 'Системна',

    // Админ
    'admin.title': 'Административен панел',
    'admin.overview': 'Преглед',
    'admin.roles': 'Роли',
    'admin.permissions': 'Разрешения',
    'admin.createRole': 'Нова роля',
  },
};

/* ─── Store ─── */

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const stored = (typeof localStorage !== 'undefined'
  ? (localStorage.getItem('locale') as Locale)
  : null) || 'en';

export const useLocaleStore = create<LocaleState>((set) => ({
  locale: stored,
  setLocale: (locale) => {
    localStorage.setItem('locale', locale);
    set({ locale });
  },
}));

/* ─── Translation function ─── */

export function t(key: string, locale?: Locale): string {
  const currentLocale = locale || useLocaleStore.getState().locale;
  return translations[currentLocale]?.[key] || translations.en[key] || key;
}

/* ─── React hook ─── */

export function useLocale() {
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return {
    locale,
    setLocale,
    t: (key: string) => t(key, locale),
  };
}
