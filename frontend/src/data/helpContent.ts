export interface PageHelp {
  title: { en: string; bg: string };
  description: { en: string; bg: string };
  tips: { en: string; bg: string }[];
  elements: Record<string, {
    title: { en: string; bg: string };
    content: { en: string; bg: string };
  }>;
}

export const helpContent: Record<string, PageHelp> = {
  '/': {
    title: { en: 'Dashboard', bg: 'Табло' },
    description: {
      en: 'Your command center. See workflows, executions, and system health at a glance.',
      bg: 'Вашият център за управление. Вижте workflows, изпълнения и състоянието на системата.',
    },
    tips: [
      { en: 'Click any stat card to navigate to the detailed view.', bg: 'Кликнете на карта със статистика, за да отидете към детайлния изглед.' },
      { en: 'Customize visible widgets using the gear icon in the top right.', bg: 'Персонализирайте видимите уиджети чрез иконата за настройки горе вдясно.' },
      { en: 'The Success Rate ring shows the ratio of completed vs failed executions.', bg: 'Пръстенът за успеваемост показва съотношението завършени/неуспешни изпълнения.' },
    ],
    elements: {
      'stats-cards': {
        title: { en: 'Statistics Cards', bg: 'Статистически карти' },
        content: { en: 'Quick overview of your workflows and executions. Click any card to see details.', bg: 'Бърз преглед на вашите workflows и изпълнения. Кликнете карта за детайли.' },
      },
      'quick-actions': {
        title: { en: 'Quick Actions', bg: 'Бързи действия' },
        content: { en: 'Shortcuts to the most common operations: create workflows, view executions, manage agents and more.', bg: 'Преки пътища към най-честите операции: създаване на workflows, преглед на изпълнения, управление на агенти.' },
      },
      'system-health': {
        title: { en: 'System Health', bg: 'Здраве на системата' },
        content: { en: 'Real-time status: WebSocket connection, online agents, queue depth, active schedules, and average execution duration.', bg: 'Статус в реално време: WebSocket връзка, онлайн агенти, опашка, активни графици и средна продължителност.' },
      },
      'widget-settings': {
        title: { en: 'Widget Settings', bg: 'Настройки на уиджети' },
        content: { en: 'Toggle which widgets are visible on your dashboard. Use "Reset to Defaults" to restore the original layout.', bg: 'Изберете кои уиджети да се показват. Използвайте "Reset to Defaults" за възстановяване.' },
      },
    },
  },

  '/workflows': {
    title: { en: 'Workflows', bg: 'Работни процеси' },
    description: {
      en: 'Create and manage automated processes. Each workflow is a series of connected steps.',
      bg: 'Създавайте и управлявайте автоматизирани процеси. Всеки workflow е поредица от свързани стъпки.',
    },
    tips: [
      { en: 'A workflow must be Published before it can be executed.', bg: 'Workflow трябва да е Published, за да може да се изпълни.' },
      { en: 'Use the search bar to quickly find workflows by name.', bg: 'Използвайте търсенето за бързо намиране по име.' },
      { en: 'Click a workflow name to open it in the visual editor.', bg: 'Кликнете име на workflow, за да го отворите в редактора.' },
    ],
    elements: {
      'create-btn': {
        title: { en: 'Create Workflow', bg: 'Създаване на Workflow' },
        content: { en: 'Creates a new empty workflow in Draft status and opens the visual editor where you can add steps.', bg: 'Създава нов празен workflow в статус Draft и отваря визуалния редактор, където добавяте стъпки.' },
      },
      'status-badge': {
        title: { en: 'Workflow Status', bg: 'Статус на Workflow' },
        content: { en: 'Draft = editable, not runnable. Published = ready to execute. Archived = read-only, can\'t run.', bg: 'Draft = може да се редактира, не може да се изпълни. Published = готов за изпълнение. Archived = само за четене.' },
      },
      'actions-menu': {
        title: { en: 'Actions', bg: 'Действия' },
        content: { en: 'Edit opens the visual editor. Execute runs the workflow. Publish makes it available for execution. Archive disables it.', bg: 'Edit отваря редактора. Execute стартира процеса. Publish го прави наличен за изпълнение. Archive го деактивира.' },
      },
    },
  },

  '/workflows/editor': {
    title: { en: 'Workflow Editor', bg: 'Редактор на Workflow' },
    description: {
      en: 'Visual drag-and-drop editor. Build automations by connecting task nodes.',
      bg: 'Визуален drag-and-drop редактор. Изграждайте автоматизации чрез свързване на задачи.',
    },
    tips: [
      { en: 'Drag task types from the palette on the right onto the canvas.', bg: 'Плъзнете типове задачи от палитрата вдясно върху платното.' },
      { en: 'Connect steps by dragging from the bottom handle of one node to the top handle of another.', bg: 'Свържете стъпки чрез влачене от долната точка на един възел към горната на друг.' },
      { en: 'Press Ctrl+S to save, Ctrl+Z to undo, Delete to remove selected.', bg: 'Натиснете Ctrl+S за запазване, Ctrl+Z за отмяна, Delete за изтриване.' },
      { en: 'Click a step to configure it in the side panel.', bg: 'Кликнете стъпка за конфигуриране в страничния панел.' },
    ],
    elements: {
      'task-palette': {
        title: { en: 'Task Palette', bg: 'Палитра със задачи' },
        content: { en: '10 task types: Web Scraping, API Request, Form Fill, Email, Database, File Ops, Custom Script, Conditional, Loop, Delay. Drag any onto the canvas.', bg: '10 типа задачи: Web Scraping, API Request, Form Fill, Email, Database, File Ops, Custom Script, Conditional, Loop, Delay. Плъзнете на платното.' },
      },
      'save-btn': {
        title: { en: 'Save', bg: 'Запазване' },
        content: { en: 'Saves the current workflow state. Keyboard shortcut: Ctrl+S (Cmd+S on Mac).', bg: 'Запазва текущото състояние. Клавишна комбинация: Ctrl+S (Cmd+S на Mac).' },
      },
      'publish-btn': {
        title: { en: 'Publish', bg: 'Публикуване' },
        content: { en: 'Makes this workflow available for execution. Only published workflows can be run manually or via triggers/schedules.', bg: 'Прави workflow-а наличен за изпълнение. Само публикувани workflows могат да се стартират.' },
      },
      'variables-panel': {
        title: { en: 'Variables', bg: 'Променливи' },
        content: { en: 'Manage workflow variables: input parameters, intermediate values, and outputs passed between steps.', bg: 'Управлявайте променливи: входни параметри, междинни стойности и изходни данни между стъпките.' },
      },
      'step-config': {
        title: { en: 'Step Configuration', bg: 'Конфигурация на стъпка' },
        content: { en: 'Configure the selected step: label, type-specific settings, and error handling (stop, skip, or redirect to another step).', bg: 'Конфигурирайте стъпката: име, специфични настройки и поведение при грешка.' },
      },
    },
  },

  '/executions': {
    title: { en: 'Executions', bg: 'Изпълнения' },
    description: {
      en: 'Monitor and manage workflow executions. See real-time status and logs.',
      bg: 'Наблюдавайте и управлявайте изпълнения. Вижте статус и логове в реално време.',
    },
    tips: [
      { en: 'Use status filter buttons to quickly find failed or running executions.', bg: 'Използвайте бутоните за филтър по статус за бързо намиране.' },
      { en: 'Click the arrow to expand an execution and see error details or live logs.', bg: 'Кликнете стрелката за разширяване и преглед на грешки или логове.' },
      { en: 'Export data to CSV using the export button.', bg: 'Експортирайте данни в CSV чрез бутона за експорт.' },
    ],
    elements: {
      'status-filter': {
        title: { en: 'Status Filters', bg: 'Филтри по статус' },
        content: { en: 'Filter by: All, Pending (waiting), Running (active), Completed (success), Failed (error), Cancelled.', bg: 'Филтрирайте по: Всички, Чакащи, Текущи, Завършени, Неуспешни, Отменени.' },
      },
      'retry-btn': {
        title: { en: 'Retry', bg: 'Повторен опит' },
        content: { en: 'Re-run a failed or cancelled execution with the same parameters. Useful after fixing the root cause.', bg: 'Стартирайте повторно неуспешно изпълнение. Полезно след отстраняване на причината.' },
      },
      'live-indicator': {
        title: { en: 'Live Indicator', bg: 'Индикатор в реално време' },
        content: { en: 'Shows WebSocket connection status. "Live" means real-time updates are active. "Offline" means the page refreshes every 5 seconds.', bg: '"Live" означава активни обновявания в реално време. "Offline" - страницата се обновява на всеки 5 секунди.' },
      },
    },
  },

  '/templates': {
    title: { en: 'Templates', bg: 'Шаблони' },
    description: {
      en: 'Pre-built workflow templates for common automation tasks. Use one to get started quickly.',
      bg: 'Готови шаблони за често срещани автоматизации. Използвайте шаблон за бърз старт.',
    },
    tips: [
      { en: 'Filter by category or difficulty to find the right template.', bg: 'Филтрирайте по категория или трудност за намиране на подходящ шаблон.' },
      { en: 'Click "Use" on a template to create a new workflow based on it.', bg: 'Кликнете "Use" за създаване на нов workflow от шаблона.' },
    ],
    elements: {},
  },

  '/triggers': {
    title: { en: 'Triggers', bg: 'Тригери' },
    description: {
      en: 'Automatically start workflows on events: schedules, webhooks, file changes, emails, and more.',
      bg: 'Автоматично стартиране на workflows при събития: графици, webhooks, промени на файлове, имейли.',
    },
    tips: [
      { en: 'Use "Fire Now" to test a trigger without waiting for the event.', bg: 'Използвайте "Fire Now" за тестване на тригер без чакане.' },
      { en: 'Cron format: minute hour day month weekday (e.g., "0 9 * * 1-5" = weekdays at 9 AM).', bg: 'Cron формат: минута час ден месец ден-от-седмицата (напр. "0 9 * * 1-5" = работни дни в 9:00).' },
    ],
    elements: {
      'trigger-type': {
        title: { en: 'Trigger Types', bg: 'Типове тригери' },
        content: { en: 'Cron (scheduled), Webhook (HTTP callback), File Watcher, Email, Database, API Poll, Manual, Event.', bg: 'Cron (по график), Webhook (HTTP), File Watcher, Email, Database, API Poll, Manual, Event.' },
      },
    },
  },

  '/schedules': {
    title: { en: 'Schedules', bg: 'Графици' },
    description: {
      en: 'Schedule workflows to run automatically at specific times using cron expressions.',
      bg: 'Планирайте автоматично изпълнение на workflows по определено време чрез cron изрази.',
    },
    tips: [
      { en: 'Common cron: "*/5 * * * *" = every 5 min, "0 */2 * * *" = every 2 hours, "0 9 * * 1-5" = weekdays 9 AM.', bg: 'Често ползвани: "*/5 * * * *" = на 5 мин, "0 */2 * * *" = на 2 часа, "0 9 * * 1-5" = работни дни 9:00.' },
    ],
    elements: {},
  },

  '/credentials': {
    title: { en: 'Credentials Vault', bg: 'Сейф за удостоверения' },
    description: {
      en: 'Securely store API keys, passwords, and tokens. All values are encrypted with AES-256.',
      bg: 'Безопасно съхранение на API ключове, пароли и токени. Всички стойности са криптирани с AES-256.',
    },
    tips: [
      { en: 'Click the eye icon to reveal a credential value temporarily.', bg: 'Кликнете иконата око за временно показване на стойност.' },
      { en: 'Credentials are referenced by name in workflow steps — they are never exposed in logs.', bg: 'Удостоверенията се референцират по име в стъпки — никога не се показват в логове.' },
    ],
    elements: {
      'credential-type': {
        title: { en: 'Credential Types', bg: 'Типове удостоверения' },
        content: { en: 'API Key, OAuth 2.0, Basic Auth, Database connection, Private Key (SSH/certs), Custom.', bg: 'API Key, OAuth 2.0, Basic Auth, Database, Private Key (SSH/сертификати), Custom.' },
      },
    },
  },

  '/agents': {
    title: { en: 'Agents', bg: 'Агенти' },
    description: {
      en: 'Manage execution agents. Agents are workers that run your automated tasks on different machines.',
      bg: 'Управление на агенти за изпълнение. Агентите изпълняват автоматизациите на различни машини.',
    },
    tips: [
      { en: 'After registering an agent, save the token immediately — it is shown only once!', bg: 'След регистрация на агент, запазете токена веднага — показва се само веднъж!' },
      { en: 'Green pulsing dot = agent is online and ready.', bg: 'Зелена пулсираща точка = агентът е онлайн и готов.' },
    ],
    elements: {},
  },

  '/users': {
    title: { en: 'Users', bg: 'Потребители' },
    description: {
      en: 'View and manage user accounts. Activate or deactivate users as needed.',
      bg: 'Преглед и управление на потребителски акаунти. Активирайте или деактивирайте потребители.',
    },
    tips: [
      { en: 'You cannot deactivate your own account.', bg: 'Не можете да деактивирате собствения си акаунт.' },
    ],
    elements: {},
  },

  '/settings': {
    title: { en: 'Settings', bg: 'Настройки' },
    description: {
      en: 'Manage your profile, appearance, and preferences.',
      bg: 'Управлявайте вашия профил, външен вид и предпочитания.',
    },
    tips: [
      { en: 'Switch between light and dark theme in the Appearance tab.', bg: 'Сменете между светла и тъмна тема в раздел Appearance.' },
    ],
    elements: {},
  },

  '/admin': {
    title: { en: 'Admin Panel', bg: 'Администрация' },
    description: {
      en: 'Organization administration: roles, permissions, and user management. Admins only.',
      bg: 'Администрация на организацията: роли, разрешения и управление на потребители. Само за администратори.',
    },
    tips: [
      { en: 'The Permissions tab shows a matrix of all roles vs permissions.', bg: 'Таб Permissions показва матрица на всички роли и разрешения.' },
      { en: 'The admin role cannot be deleted.', bg: 'Администраторската роля не може да бъде изтрита.' },
    ],
    elements: {},
  },

  '/audit-log': {
    title: { en: 'Audit Log', bg: 'Одит лог' },
    description: {
      en: 'Complete history of all system actions for compliance and debugging.',
      bg: 'Пълна история на всички действия в системата за одит и дебъг.',
    },
    tips: [
      { en: 'Expand a row to see the exact changes (old vs new values).', bg: 'Разширете ред за преглед на промените (стари vs нови стойности).' },
    ],
    elements: {},
  },

  '/plugins': {
    title: { en: 'Plugins', bg: 'Плъгини' },
    description: {
      en: 'Extend the platform with additional task types and functionality.',
      bg: 'Разширете платформата с допълнителни типове задачи и функционалност.',
    },
    tips: [
      { en: 'Toggle a plugin on/off with the power icon.', bg: 'Включете/изключете плъгин с иконата за захранване.' },
    ],
    elements: {},
  },
};

// Onboarding tour steps
export const onboardingSteps = [
  {
    target: 'sidebar',
    title: { en: 'Navigation', bg: 'Навигация' },
    content: {
      en: 'Use the sidebar to navigate between sections: Dashboard, Workflows, Executions, and more.',
      bg: 'Използвайте страничната лента за навигация: Табло, Workflows, Изпълнения и други.',
    },
  },
  {
    target: 'dashboard',
    title: { en: 'Dashboard', bg: 'Табло' },
    content: {
      en: 'Your starting point. See statistics, system health, and recent activity at a glance.',
      bg: 'Вашата начална точка. Преглед на статистики, състояние на системата и последна активност.',
    },
  },
  {
    target: 'workflows',
    title: { en: 'Workflows', bg: 'Работни процеси' },
    content: {
      en: 'Create automations here. Each workflow is a series of connected steps (e.g., scrape data, transform, save).',
      bg: 'Създавайте автоматизации тук. Всеки workflow е поредица от свързани стъпки.',
    },
  },
  {
    target: 'executions',
    title: { en: 'Executions', bg: 'Изпълнения' },
    content: {
      en: 'Monitor your running and past executions. See logs, retry failed ones, or export data.',
      bg: 'Наблюдавайте текущи и минали изпълнения. Вижте логове, повторете неуспешни или експортирайте.',
    },
  },
  {
    target: 'credentials',
    title: { en: 'Credentials', bg: 'Удостоверения' },
    content: {
      en: 'Store API keys and passwords securely. They are encrypted and referenced by name in workflows.',
      bg: 'Съхранявайте API ключове и пароли сигурно. Те са криптирани и се използват по име в workflows.',
    },
  },
  {
    target: 'chat',
    title: { en: 'AI Assistant', bg: 'AI Помощник' },
    content: {
      en: 'Need help? Click the chat button in the bottom-right corner to ask the AI assistant any question about the platform.',
      bg: 'Нужна ви е помощ? Кликнете чат бутона долу вдясно и попитайте AI помощника за платформата.',
    },
  },
];

// Suggested chat questions per page
export const suggestedQuestions: Record<string, { en: string; bg: string }[]> = {
  '/': [
    { en: 'How do I create my first workflow?', bg: 'Как да създам първия си workflow?' },
    { en: 'What do the dashboard statistics mean?', bg: 'Какво означават статистиките на таблото?' },
    { en: 'How do I customize the dashboard?', bg: 'Как да персонализирам таблото?' },
  ],
  '/workflows': [
    { en: 'How do I publish a workflow?', bg: 'Как да публикувам workflow?' },
    { en: 'What is the difference between Draft and Published?', bg: 'Каква е разликата между Draft и Published?' },
    { en: 'Can I duplicate a workflow?', bg: 'Мога ли да дублирам workflow?' },
  ],
  '/executions': [
    { en: 'Why did my execution fail?', bg: 'Защо изпълнението ми се провали?' },
    { en: 'How do I retry a failed execution?', bg: 'Как да повторя неуспешно изпълнение?' },
    { en: 'Can I see real-time logs?', bg: 'Мога ли да виждам логове в реално време?' },
  ],
  '/credentials': [
    { en: 'How are my credentials encrypted?', bg: 'Как са криптирани удостоверенията ми?' },
    { en: 'What types of credentials can I store?', bg: 'Какви типове удостоверения мога да съхранявам?' },
  ],
  '/triggers': [
    { en: 'What is a cron expression?', bg: 'Какво е cron израз?' },
    { en: 'How do webhooks work?', bg: 'Как работят webhooks?' },
  ],
};
