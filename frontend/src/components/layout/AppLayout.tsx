import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import GlobalSearch from '@/components/GlobalSearch';
import ChatAssistant from '@/components/chat/ChatAssistant';
import OnboardingTour from '@/components/help/OnboardingTour';
import { useHelpStore } from '@/stores/helpStore';

export default function AppLayout() {
  const [searchOpen, setSearchOpen] = useState(false);
  const { onboardingCompleted, startOnboarding } = useHelpStore();

  useEffect(() => {
    if (!onboardingCompleted) {
      const timer = setTimeout(() => startOnboarding(), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

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
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar onSearchOpen={() => setSearchOpen(true)} />
        <main className="flex-1 overflow-auto">
          <div className="p-6 max-w-7xl mx-auto">
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
