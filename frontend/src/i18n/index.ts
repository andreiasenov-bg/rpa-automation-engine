/**
 * Lightweight i18n system for RPA Engine.
 *
 * Usage:
 *   import { t, useLocale } from '@/i18n';
 *   const label = t('dashboard.title');  // "Dashboard" or "Ð¢Ð°Ð±Ð»Ð¾"
 *
 *   // In a component:
 *   const { locale, setLocale, t } = useLocale();
 */

import { create } from 'zustand';

export type Locale = 'en' | 'bg';

type TranslationMap = Record<string, string>;

/* âââ Translation dictionaries âââ */

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
    'nav.rpaList': 'RPA List',
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
    'nav.reports': 'Reports',
    'nav.apiHealth': 'API Health',
    'nav.profiler': 'Profiler',
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
    'settings.apiKeys': 'API Keys',
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
    // ÐÐ±ÑÐ¸
    'common.save': 'ÐÐ°Ð¿Ð°Ð·Ð¸',
    'common.cancel': 'ÐÑÐºÐ°Ð·',
    'common.delete': 'ÐÐ·ÑÑÐ¸Ð¹',
    'common.create': 'Ð¡ÑÐ·Ð´Ð°Ð¹',
    'common.edit': 'Ð ÐµÐ´Ð°ÐºÑÐ¸ÑÐ°Ð¹',
    'common.search': 'Ð¢ÑÑÑÐµÐ½Ðµ',
    'common.loading': 'ÐÐ°ÑÐµÐ¶Ð´Ð°Ð½Ðµ...',
    'common.noResults': 'ÐÑÐ¼Ð° ÑÐµÐ·ÑÐ»ÑÐ°ÑÐ¸',
    'common.confirm': 'ÐÐ¾ÑÐ²ÑÑÐ´Ð¸',
    'common.back': 'ÐÐ°Ð·Ð°Ð´',
    'common.next': 'ÐÐ°Ð¿ÑÐµÐ´',
    'common.export': 'ÐÐºÑÐ¿Ð¾ÑÑ',
    'common.refresh': 'ÐÐ±Ð½Ð¾Ð²Ð¸',
    'common.close': 'ÐÐ°ÑÐ²Ð¾ÑÐ¸',
    'common.yes': 'ÐÐ°',
    'common.no': 'ÐÐµ',
    'common.all': 'ÐÑÐ¸ÑÐºÐ¸',
    'common.enabled': 'ÐÐºÐ»ÑÑÐµÐ½Ð¾',
    'common.disabled': 'ÐÐ·ÐºÐ»ÑÑÐµÐ½Ð¾',
    'common.active': 'ÐÐºÑÐ¸Ð²Ð½Ð¾',
    'common.inactive': 'ÐÐµÐ°ÐºÑÐ¸Ð²Ð½Ð¾',

    // ÐÐ°Ð²Ð¸Ð³Ð°ÑÐ¸Ñ
    'nav.dashboard': 'Ð¢Ð°Ð±Ð»Ð¾',
    'nav.workflows': 'ÐÑÐ¾ÑÐµÑÐ¸',
    'nav.rpaList': 'RPA Ð Ð¾Ð±Ð¾ÑÐ¸',
    'nav.executions': 'ÐÐ·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ',
    'nav.templates': 'Ð¨Ð°Ð±Ð»Ð¾Ð½Ð¸',
    'nav.aiCreator': 'AI Ð¡ÑÐ·Ð´Ð°ÑÐµÐ»',
    'nav.triggers': 'Ð¢ÑÐ¸Ð³ÐµÑÐ¸',
    'nav.schedules': 'Ð Ð°Ð·Ð¿Ð¸ÑÐ°Ð½Ð¸Ñ',
    'nav.integrations': 'ÐÐ½ÑÐµÐ³ÑÐ°ÑÐ¸Ð¸',
    'nav.credentials': 'ÐÐ´ÐµÐ½ÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¸Ð¸',
    'nav.agents': 'ÐÐ³ÐµÐ½ÑÐ¸',
    'nav.users': 'ÐÐ¾ÑÑÐµÐ±Ð¸ÑÐµÐ»Ð¸',
    'nav.notifications': 'ÐÐ·Ð²ÐµÑÑÐ¸Ñ',
    'nav.auditLog': 'ÐÐ´Ð¸Ñ Ð»Ð¾Ð³',
    'nav.plugins': 'ÐÐ»ÑÐ³Ð¸Ð½Ð¸',
    'nav.apiDocs': 'API ÐÐ¾ÐºÑÐ¼ÐµÐ½ÑÐ°ÑÐ¸Ñ',
    'nav.reports': 'ÐÑÑÐµÑÐ¸',
    'nav.admin': 'ÐÐ´Ð¼Ð¸Ð½',
    'nav.settings': 'ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸',
    'nav.logout': 'ÐÐ·ÑÐ¾Ð´',

    // ÐÐ²ÑÐµÐ½ÑÐ¸ÐºÐ°ÑÐ¸Ñ
    'auth.login': 'ÐÑÐ¾Ð´',
    'auth.register': 'Ð ÐµÐ³Ð¸ÑÑÑÐ°ÑÐ¸Ñ',
    'auth.email': 'ÐÐ¼ÐµÐ¹Ð»',
    'auth.password': 'ÐÐ°ÑÐ¾Ð»Ð°',
    'auth.confirmPassword': 'ÐÐ¾ÑÐ²ÑÑÐ´Ð¸ Ð¿Ð°ÑÐ¾Ð»Ð°',
    'auth.firstName': 'ÐÐ¼Ðµ',
    'auth.lastName': 'Ð¤Ð°Ð¼Ð¸Ð»Ð¸Ñ',
    'auth.orgName': 'ÐÐ¼Ðµ Ð½Ð° Ð¾ÑÐ³Ð°Ð½Ð¸Ð·Ð°ÑÐ¸Ñ',
    'auth.forgotPassword': 'ÐÐ°Ð±ÑÐ°Ð²ÐµÐ½Ð° Ð¿Ð°ÑÐ¾Ð»Ð°?',
    'auth.noAccount': 'ÐÑÐ¼Ð°ÑÐµ Ð°ÐºÐ°ÑÐ½Ñ?',
    'auth.hasAccount': 'ÐÐµÑÐµ Ð¸Ð¼Ð°ÑÐµ Ð°ÐºÐ°ÑÐ½Ñ?',
    'auth.loginSubtitle': 'ÐÐ»ÐµÐ·ÑÐµ Ð² Ð°ÐºÐ°ÑÐ½ÑÐ° ÑÐ¸',
    'auth.signingIn': 'ÐÐ»Ð¸Ð·Ð°Ð½Ðµ...',
    'auth.registerSubtitle': 'Ð¡ÑÐ·Ð´Ð°Ð¹ÑÐµ Ð°ÐºÐ°ÑÐ½Ñ',
    'auth.creatingAccount': 'Ð¡ÑÐ·Ð´Ð°Ð²Ð°Ð½Ðµ Ð½Ð° Ð°ÐºÐ°ÑÐ½Ñ...',
    'auth.createAccount': 'Ð¡ÑÐ·Ð´Ð°Ð¹ Ð°ÐºÐ°ÑÐ½Ñ',

    // Ð¢Ð°Ð±Ð»Ð¾
    'dashboard.title': 'Ð¢Ð°Ð±Ð»Ð¾',
    'dashboard.subtitle': 'ÐÑÐµÐ³Ð»ÐµÐ´ Ð½Ð° Ð²Ð°ÑÐ°ÑÐ° RPA Ð¿Ð»Ð°ÑÑÐ¾ÑÐ¼Ð°',
    'dashboard.totalWorkflows': 'ÐÐ±ÑÐ¾ Ð¿ÑÐ¾ÑÐµÑÐ¸',
    'dashboard.activeWorkflows': 'ÐÐºÑÐ¸Ð²Ð½Ð¸',
    'dashboard.totalExecutions': 'ÐÐ±ÑÐ¾ Ð¸Ð·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ',
    'dashboard.running': 'ÐÐ·Ð¿ÑÐ»Ð½ÑÐ²Ð°ÑÐ¸ ÑÐµ',
    'dashboard.completed': 'ÐÐ°Ð²ÑÑÑÐµÐ½Ð¸',
    'dashboard.failed': 'ÐÐµÑÑÐ¿ÐµÑÐ½Ð¸',
    'dashboard.recentExecutions': 'ÐÐ¾ÑÐ»ÐµÐ´Ð½Ð¸ Ð¸Ð·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ',

    // ÐÑÐ¾ÑÐµÑÐ¸
    'workflows.title': 'ÐÑÐ¾ÑÐµÑÐ¸',
    'workflows.new': 'ÐÐ¾Ð² Ð¿ÑÐ¾ÑÐµÑ',
    'workflows.editor': 'Ð ÐµÐ´Ð°ÐºÑÐ¾Ñ Ð½Ð° Ð¿ÑÐ¾ÑÐµÑÐ¸',
    'workflows.publish': 'ÐÑÐ±Ð»Ð¸ÐºÑÐ²Ð°Ð¹',
    'workflows.archive': 'ÐÑÑÐ¸Ð²Ð¸ÑÐ°Ð¹',
    'workflows.execute': 'ÐÐ·Ð¿ÑÐ»Ð½Ð¸',
    'workflows.clone': 'ÐÐ»Ð¾Ð½Ð¸ÑÐ°Ð¹',
    'workflows.delete': 'ÐÐ·ÑÑÐ¸Ð¹ Ð¿ÑÐ¾ÑÐµÑ',

    // ÐÐ·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ
    'executions.title': 'ÐÐ·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ',
    'executions.retry': 'ÐÐ¾Ð²ÑÐ¾ÑÐ¸',
    'executions.cancel': 'ÐÑÐ¼ÐµÐ½Ð¸',
    'executions.logs': 'ÐÐ¾Ð³Ð¾Ð²Ðµ',
    'executions.status.pending': 'Ð§Ð°ÐºÐ°ÑÐ¾',
    'executions.status.running': 'ÐÐ·Ð¿ÑÐ»Ð½ÑÐ²Ð° ÑÐµ',
    'executions.status.completed': 'ÐÐ°Ð²ÑÑÑÐµÐ½Ð¾',
    'executions.status.failed': 'ÐÐµÑÑÐ¿ÐµÑÐ½Ð¾',
    'executions.status.cancelled': 'ÐÑÐ¼ÐµÐ½ÐµÐ½Ð¾',

    // ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸
    'settings.title': 'ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸',
    'settings.profile': 'ÐÑÐ¾ÑÐ¸Ð»',
    'settings.organization': 'ÐÑÐ³Ð°Ð½Ð¸Ð·Ð°ÑÐ¸Ñ',
    'settings.security': 'Ð¡Ð¸Ð³ÑÑÐ½Ð¾ÑÑ',
    'settings.apiKeys': 'API ÐÐ»ÑÑÐ¾Ð²Ðµ',
    'settings.notifications': 'ÐÐ·Ð²ÐµÑÑÐ¸Ñ',
    'settings.appearance': 'ÐÑÐ½ÑÐµÐ½ Ð²Ð¸Ð´',
    'settings.theme': 'Ð¢ÐµÐ¼Ð°',
    'settings.themeDesc': 'ÐÐ·Ð±ÐµÑÐµÑÐµ Ð¿ÑÐµÐ´Ð¿Ð¾ÑÐ¸ÑÐ°Ð½Ð°ÑÐ° ÑÐ²ÐµÑÐ¾Ð²Ð° ÑÑÐµÐ¼Ð°',
    'settings.light': 'Ð¡Ð²ÐµÑÐ»Ð°',
    'settings.dark': 'Ð¢ÑÐ¼Ð½Ð°',
    'settings.system': 'Ð¡Ð¸ÑÑÐµÐ¼Ð½Ð°',
    'settings.subtitle': 'Ð£Ð¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ðµ Ð½Ð° Ð°ÐºÐ°ÑÐ½Ñ Ð¸ Ð¾ÑÐ³Ð°Ð½Ð¸Ð·Ð°ÑÐ¸Ñ',
    'settings.personalInfo': 'ÐÐ¸ÑÐ½Ð° Ð¸Ð½ÑÐ¾ÑÐ¼Ð°ÑÐ¸Ñ',
    'settings.emailReadonly': 'ÐÐ¼ÐµÐ¹Ð»ÑÑ Ð½Ðµ Ð¼Ð¾Ð¶Ðµ Ð´Ð° Ð±ÑÐ´Ðµ Ð¿ÑÐ¾Ð¼ÐµÐ½ÐµÐ½',
    'settings.saved': 'ÐÐ°Ð¿Ð°Ð·ÐµÐ½Ð¾',
    'settings.language': 'ÐÐ·Ð¸Ðº',
    'settings.languageDesc': 'ÐÐ·Ð±ÐµÑÐµÑÐµ Ð¿ÑÐµÐ´Ð¿Ð¾ÑÐ¸ÑÐ°Ð½Ð¸Ñ ÐµÐ·Ð¸Ðº',

    // ÐÑÐ¾ÑÐµÑÐ¸ Ð´Ð¾Ð¿ÑÐ»Ð½Ð¸ÑÐµÐ»Ð½Ð¸
    'workflows.searchPlaceholder': 'Ð¢ÑÑÑÐµÐ½Ðµ Ð½Ð° Ð¿ÑÐ¾ÑÐµÑÐ¸...',
    'workflows.noWorkflows': 'ÐÑÐ¼Ð° Ð¿ÑÐ¾ÑÐµÑÐ¸',
    'workflows.noMatch': 'ÐÑÐ¼Ð° ÑÑÐ²Ð¿Ð°Ð´ÐµÐ½Ð¸Ñ',
    'workflows.createFirst': 'Ð¡ÑÐ·Ð´Ð°Ð¹ÑÐµ Ð¿ÑÑÐ²Ð¸Ñ ÑÐ¸ Ð¿ÑÐ¾ÑÐµÑ',

    // ÐÐ´Ð¼Ð¸Ð½
    'admin.title': 'ÐÐ´Ð¼Ð¸Ð½Ð¸ÑÑÑÐ°ÑÐ¸Ð²ÐµÐ½ Ð¿Ð°Ð½ÐµÐ»',
    'admin.overview': 'ÐÑÐµÐ³Ð»ÐµÐ´',
    'admin.roles': 'Ð Ð¾Ð»Ð¸',
    'admin.permissions': 'Ð Ð°Ð·ÑÐµÑÐµÐ½Ð¸Ñ',
    'admin.createRole': 'ÐÐ¾Ð²Ð° ÑÐ¾Ð»Ñ',

    // ÐÐ½Ð°Ð»Ð¸ÑÐ¸ÐºÐ°
    'analytics.title': 'ÐÐ½Ð°Ð»Ð¸ÑÐ¸ÐºÐ°',
    'analytics.avgDuration': 'Ð¡ÑÐµÐ´Ð½Ð° Ð¿ÑÐ¾Ð´ÑÐ»Ð¶.',
    'analytics.executionTimeline': 'Ð¥ÑÐ¾Ð½Ð¾Ð»Ð¾Ð³Ð¸Ñ Ð½Ð° Ð¸Ð·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ',
    'analytics.successRate': 'ÐÑÐ¾ÑÐµÐ½Ñ ÑÑÐ¿ÐµÑ',
    'analytics.workflowPerformance': 'ÐÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»Ð½Ð¾ÑÑ Ð½Ð° Ð¿ÑÐ¾ÑÐµÑÐ¸',

    // ÐÐºÑÐ¸Ð²Ð½Ð¾ÑÑ
    'activity.title': 'ÐÐ¾ÑÐ»ÐµÐ´Ð½Ð° Ð°ÐºÑÐ¸Ð²Ð½Ð¾ÑÑ',
    'activity.noActivity': 'ÐÑÐ¼Ð° ÑÐºÐ¾ÑÐ¾ÑÐ½Ð° Ð°ÐºÑÐ¸Ð²Ð½Ð¾ÑÑ',

    // Ð¢ÑÑÑÐµÐ½Ðµ
    'search.placeholder': 'Ð¢ÑÑÑÐµÐ½Ðµ Ð½Ð° Ð¿ÑÐ¾ÑÐµÑÐ¸, Ð¸Ð·Ð¿ÑÐ»Ð½ÐµÐ½Ð¸Ñ, Ð°Ð³ÐµÐ½ÑÐ¸...',
    'search.hint': 'ÐÑÐ²ÐµÐ´ÐµÑÐµ Ð·Ð° ÑÑÑÑÐµÐ½Ðµ Ð² ÑÐ°Ð±Ð¾ÑÐ½Ð°ÑÐ° ÑÑÐµÐ´Ð°',
    'search.shortcutHint': 'Ð·Ð° Ð¿ÑÐµÐ²ÐºÐ»ÑÑÐ²Ð°Ð½Ðµ Ð½Ð° ÑÑÑÑÐµÐ½ÐµÑÐ¾',

    // ÐÐ·Ð²ÐµÑÑÐ¸Ñ
    'notifications.title': 'ÐÐ·Ð²ÐµÑÑÐ¸Ñ',
    'notifications.markAllRead': 'ÐÑÐ¾ÑÐµÑÐ¸ Ð²ÑÐ¸ÑÐºÐ¸',
    'notifications.empty': 'ÐÑÐ¼Ð° Ð¸Ð·Ð²ÐµÑÑÐ¸Ñ',
    'notifications.viewAll': 'ÐÐ¸Ð¶ Ð²ÑÐ¸ÑÐºÐ¸ Ð¸Ð·Ð²ÐµÑÑÐ¸Ñ',
  },
};

/* âââ Store âââ */

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

/* âââ Translation function âââ */

export function t(key: string, locale?: Locale): string {
  const currentLocale = locale || useLocaleStore.getState().locale;
  return translations[currentLocale]?.[key] || translations.en[key] || key;
}

/* âââ React hook âââ */

export function useLocale() {
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return {
    locale,
    setLocale,
    t: (key: string) => t(key, locale),
  };
}
