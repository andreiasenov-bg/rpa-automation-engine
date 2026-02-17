import { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import GlobalSearch from '@/components/GlobalSearch';
import ChatAssistant from '@/components/chat/ChatAssistant';
import OnboardingTour from '@/components/help/OnboardingTour';
import { useHelpStore } from '@/stores/helpStore';

export default function AppLayout() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { onboardingCompleted, startOnboarding } = useHelpStore();
  const location = useLocation();

  useEffect(() => {
    if (!onboardingCompleted) {
      const timer = setTimeout(() => startOnboarding(), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Global Cmd/Ctrl+K listener to open search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleCloseSearch = useCallback(() => setSearchOpen(false), []);

  return (
    <div className="flex min-h-screen">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar
          onSearchOpen={() => setSearchOpen(true)}
          onMenuOpen={() => setSidebarOpen(true)}
        />
        <main className="flex-1 overflow-auto">
          <div className="p-3 sm:p-4 md:p-6 max-w-7xl mx-auto">
            <Breadcrumb />
            <Outlet />
          </div>
        </main>
      </div>
      {searchOpen && <GlobalSearch onClose={handleCloseSearch} />}
      <ChatAssistant />
      <OnboardingTour />
    </div>
  );
}
