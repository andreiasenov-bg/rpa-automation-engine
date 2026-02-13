/**
 * TopBar — Global header with search trigger + notification center.
 */

import { Search, Command } from 'lucide-react';
import NotificationCenter from '@/components/NotificationCenter';
import { useLocale } from '@/i18n';

export default function TopBar({ onSearchOpen }: { onSearchOpen: () => void }) {
  const { t } = useLocale();

  return (
    <header className="h-14 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between px-6">
      {/* Search trigger */}
      <button
        onClick={onSearchOpen}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 text-sm text-slate-400 hover:border-slate-300 hover:text-slate-500 transition-colors w-64"
      >
        <Search className="w-4 h-4" />
        <span className="flex-1 text-left">{t('search.placeholder')}</span>
        <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono text-slate-400">
          <Command className="w-3 h-3" />K
        </kbd>
      </button>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <NotificationCenter />
      </div>
    </header>
  );
}
