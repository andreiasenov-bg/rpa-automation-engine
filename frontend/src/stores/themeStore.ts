import { create } from 'zustand';

type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  resolved: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
}

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolve(theme: Theme): 'light' | 'dark' {
  return theme === 'system' ? getSystemTheme() : theme;
}

function applyTheme(resolved: 'light' | 'dark') {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', resolved === 'dark');
}

const stored = (typeof localStorage !== 'undefined'
  ? (localStorage.getItem('theme') as Theme)
  : null) || 'light';
const initialResolved = resolve(stored);
applyTheme(initialResolved);

export const useThemeStore = create<ThemeState>((set) => ({
  theme: stored,
  resolved: initialResolved,
  setTheme: (theme) => {
    const resolved = resolve(theme);
    localStorage.setItem('theme', theme);
    applyTheme(resolved);
    set({ theme, resolved });
  },
}));

// Listen for system theme changes
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const state = useThemeStore.getState();
    if (state.theme === 'system') {
      const resolved = getSystemTheme();
      applyTheme(resolved);
      useThemeStore.setState({ resolved });
    }
  });
}
