/**
 * layoutStore — Zustand store for global layout state.
 *
 * Manages:
 *  - Sidebar open/close (mobile drawer)
 *  - Sidebar collapsed/expanded (desktop compact mode — future)
 *  - Global search overlay
 *  - Any layout-level transient UI state
 *
 * Usage:
 *   const { sidebarOpen, toggleSidebar, closeSidebar } = useLayoutStore();
 */

import { create } from 'zustand';

interface LayoutState {
  /* ─── Sidebar (mobile drawer) ─── */
  sidebarOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;

  /* ─── Sidebar collapsed (desktop compact mode — future) ─── */
  sidebarCollapsed: boolean;
  toggleSidebarCollapsed: () => void;

  /* ─── Global search ─── */
  searchOpen: boolean;
  openSearch: () => void;
  closeSearch: () => void;
  toggleSearch: () => void;
}

export const useLayoutStore = create<LayoutState>((set) => ({
  /* ─── Sidebar (mobile drawer) ─── */
  sidebarOpen: false,
  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  /* ─── Sidebar collapsed ─── */
  sidebarCollapsed: false,
  toggleSidebarCollapsed: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  /* ─── Global search ─── */
  searchOpen: false,
  openSearch: () => set({ searchOpen: true }),
  closeSearch: () => set({ searchOpen: false }),
  toggleSearch: () => set((s) => ({ searchOpen: !s.searchOpen })),
}));
