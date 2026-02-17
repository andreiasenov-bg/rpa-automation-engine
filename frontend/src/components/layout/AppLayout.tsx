/**
 * AppLayout — Root layout for all authenticated pages.
 *
 * Manages:
 *  - Sidebar (drawer on mobile via layoutStore, inline on desktop)
 *  - TopBar with hamburger + search
 *  - Main content area with responsive padding
 *  - Global overlays (search, chat, onboarding)
 *
 * Responsive breakpoint: lg (1024px)
 *   < lg → sidebar hidden, hamburger visible, drawer mode
 *   ≥ lg → sidebar inline, hamburger hidden
 */

import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import GlobalSearch from '@/components/GlobalSearch';
import ChatAssistant from '@/components/chat/ChatAssistant';
import OnboardingTour from '@/components/help/OnboardingTour';
import { useHelpStore } from '@/stores/helpStore';
import { useLayoutStore } from '@/stores/layoutStore';

export default function AppLayout() {
  const { sidebarOpen, closeSidebar, searchOpen, closeSearch, toggleSearch } =
    useLayoutStore();
  const { onboardingCompleted, startOnboarding } = useHelpStore();
  const location = useLocation();

  // Auto-start onboarding for new users
  useEffect(() => {
    if (!onboardingCompleted) {
      const timer = setTimeout(() => startOnboarding(), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    closeSidebar();
  }, [location.pathname]);

  // Global Cmd/Ctrl+K listener to open search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleSearch();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleSearch]);

  return (
    <div className="flex min-h-screen">
      {/* Mobile overlay — closes sidebar on tap */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={closeSidebar}
        />
      )}

      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar />
        <main className="flex-1 overflow-auto">
          <div className="p-3 sm:p-4 md:p-6 max-w-7xl mx-auto">
            <Breadcrumb />
            <Outlet />
          </div>
        </main>
      </div>

      {searchOpen && <GlobalSearch onClose={closeSearch} />}
      <ChatAssistant />
      <OnboardingTour />
    </div>
  );
}
