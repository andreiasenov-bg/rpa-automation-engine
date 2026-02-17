/**
 * TopBar — Global header with search trigger + notification center.
 * Includes hamburger menu button on mobile.
 */

import { Search, Command, Menu } from 'lucide-react';
import NotificationCenter from '@/components/NotificationCenter';
import { useLocale } from '@/i18n';

interface TopBarProps {
  onSearchOpen: () => void;
  onMenuOpen: () => void;
}

export default function TopBar({ onSearchOpen, onMenuOpen }: TopBarProps) {
  const { t } = useLocale();

  return (
    <header className="h-14 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between px-3 sm:px-4 md:px-6 gap-2">
      {/* Left side: hamburger + search */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {/* Mobile hamburger */}
        <button
          onClick={onMenuOpen}
          className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 lg:hidden flex-shrink-0"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5 text-slate-600 dark:text-slate-300" />
        </button>

        {/* Search trigger */}
        <button
          onClick={onSearchOpen}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 text-sm text-slate-400 hover:border-slate-300 hover:text-slate-500 transition-colors w-full max-w-[16rem] sm:max-w-xs md:w-64"
        >
          <Search className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1 text-left truncate">{t('search.placeholder')}</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono text-slate-400">
            <Command className="w-3 h-3" />K
          </kbd>
        </button>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <NotificationCenter />
      </div>
    </header>
  );
}
