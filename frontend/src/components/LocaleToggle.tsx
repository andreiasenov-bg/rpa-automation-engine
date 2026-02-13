import { useLocaleStore, type Locale } from '@/i18n';

const locales: { value: Locale; label: string; flag: string }[] = [
  { value: 'en', label: 'English', flag: 'EN' },
  { value: 'bg', label: 'Български', flag: 'BG' },
];

export default function LocaleToggle() {
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return (
    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
      {locales.map(({ value, label, flag }) => (
        <button
          key={value}
          onClick={() => setLocale(value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition ${
            locale === value
              ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
          title={label}
        >
          <span className="font-bold text-[10px]">{flag}</span>
          {label}
        </button>
      ))}
    </div>
  );
}
