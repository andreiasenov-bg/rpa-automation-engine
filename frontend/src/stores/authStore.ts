import { create } from 'zustand';
import type { User } from '@/types';
import { authApi } from '@/api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName: string, lastName: string, orgName: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await authApi.login({ email, password });
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);

      const user = await authApi.me();
      localStorage.setItem('user_id', user.id);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Login failed';
      set({ error: message, isLoading: false, isAuthenticated: false });
      throw err;
    }
  },

  register: async (email, password, firstName, lastName, orgName) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await authApi.register({
        email, password,
        first_name: firstName,
        last_name: lastName,
        org_name: orgName,
      });
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);

      const user = await authApi.me();
      localStorage.setItem('user_id', user.id);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Registration failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
    set({ user: null, isAuthenticated: false, error: null });
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }

    set({ isLoading: true });
    try {
      const user = await authApi.me();
      localStorage.setItem('user_id', user.id);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
