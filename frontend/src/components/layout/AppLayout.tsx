import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import GlobalSearch from '@/components/GlobalSearch';

export default function AppLayout() {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar onSearchOpen={() => setSearchOpen(true)} />
        <main className="flex-1 overflow-auto">
          <div className="p-6 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
      {searchOpen && <GlobalSearch />}
    </div>
  );
}
