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
    'nav.aiCreator': 'AI Creator',
    'nav.triggers': 'Triggers',
    'nav.schedules': 'Schedules',
    'nav.integrations': 'Integrations',
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
    'auth.loginSubtitle': 'Sign in to your account',
    'auth.signingIn': 'Signing in...',
    'auth.registerSubtitle': 'Create your account',
    'auth.creatingAccount': 'Creating account...',
    'auth.createAccount': 'Create account',

    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.subtitle': 'Overview of your RPA automation platform',
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
    'settings.subtitle': 'Manage your account and organization',
    'settings.personalInfo': 'Personal Information',
    'settings.emailReadonly': 'Email cannot be changed',
    'settings.saved': 'Saved',
    'settings.language': 'Language',
    'settings.languageDesc': 'Choose your preferred language',

    // Workflows extra
    'workflows.searchPlaceholder': 'Search workflows...',
    'workflows.noWorkflows': 'No workflows yet',
    'workflows.noMatch': 'No workflows match your search',
    'workflows.createFirst': 'Create your first workflow',

    // Admin
    'admin.title': 'Admin Panel',
    'admin.overview': 'Overview',
    'admin.roles': 'Roles',
    'admin.permissions': 'Permissions',
    'admin.createRole': 'New Role',

    // Analytics
    'analytics.title': 'Analytics',
    'analytics.avgDuration': 'Avg Duration',
    'analytics.executionTimeline': 'Execution Timeline',
    'analytics.successRate': 'Success Rate',
    'analytics.workflowPerformance': 'Workflow Performance',

    // Activity
    'activity.title': 'Recent Activity',
    'activity.noActivity': 'No recent activity',

    // Search
    'search.placeholder': 'Search workflows, executions, agents...',
    'search.hint': 'Type to search across your workspace',
    'search.shortcutHint': 'to toggle search',

    // Notifications
    'notifications.title': 'Notifications',
    'notifications.markAllRead': 'Mark all read',
    'notifications.empty': 'No notifications yet',
    'notifications.viewAll': 'View all notifications',
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
    'nav.aiCreator': 'AI Създател',
    'nav.triggers': 'Тригери',
    'nav.schedules': 'Разписания',
    'nav.integrations': 'Интеграции',
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
    'auth.loginSubtitle': 'Влезте в акаунта си',
    'auth.signingIn': 'Влизане...',
    'auth.registerSubtitle': 'Създайте акаунт',
    'auth.creatingAccount': 'Създаване на акаунт...',
    'auth.createAccount': 'Създай акаунт',

    // Табло
    'dashboard.title': 'Табло',
    'dashboard.subtitle': 'Преглед на вашата RPA платформа',
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
    'settings.subtitle': 'Управление на акаунт и организация',
    'settings.personalInfo': 'Лична информация',
    'settings.emailReadonly': 'Имейлът не може да бъде променен',
    'settings.saved': 'Запазено',
    'settings.language': 'Език',
    'settings.languageDesc': 'Изберете предпочитания език',

    // Процеси допълнителни
    'workflows.searchPlaceholder': 'Търсене на процеси...',
    'workflows.noWorkflows': 'Няма процеси',
    'workflows.noMatch': 'Няма съвпадения',
    'workflows.createFirst': 'Създайте първия си процес',

    // Админ
    'admin.title': 'Административен панел',
    'admin.overview': 'Преглед',
    'admin.roles': 'Роли',
    'admin.permissions': 'Разрешения',
    'admin.createRole': 'Нова роля',

    // Аналитика
    'analytics.title': 'Аналитика',
    'analytics.avgDuration': 'Средна продълж.',
    'analytics.executionTimeline': 'Хронология на изпълнения',
    'analytics.successRate': 'Процент успех',
    'analytics.workflowPerformance': 'Производителност на процеси',

    // Активност
    'activity.title': 'Последна активност',
    'activity.noActivity': 'Няма скорошна активност',

    // Търсене
    'search.placeholder': 'Търсене на процеси, изпълнения, агенти...',
    'search.hint': 'Въведете за търсене в работната среда',
    'search.shortcutHint': 'за превключване на търсенето',

    // Известия
    'notifications.title': 'Известия',
    'notifications.markAllRead': 'Прочети всички',
    'notifications.empty': 'Няма известия',
    'notifications.viewAll': 'Виж всички известия',
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
