import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserProfile } from '@kohwai/shared/types';

interface AuthState {
  accessToken:  string | null;
  refreshToken: string | null;
  user:         UserProfile | null;
  setAuth: (access: string, refresh: string, user: UserProfile) => void;
  clearAuth: () => void;
}

function syncCookies(accessToken: string | null, roles: string[]) {
  if (typeof document === 'undefined') return;
  if (accessToken) {
    document.cookie = `access_token=${accessToken}; path=/; max-age=2592000; SameSite=Lax`;
    document.cookie = `user_roles=${roles.join(',')}; path=/; max-age=2592000; SameSite=Lax`;
  } else {
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'user_roles=; path=/; max-age=0';
  }
}

function syncPlainStorage(accessToken: string | null, refreshToken: string | null) {
  if (typeof window === 'undefined') return;
  if (accessToken) {
    window.localStorage.setItem('access_token', accessToken);
    if (refreshToken) window.localStorage.setItem('refresh_token', refreshToken);
  } else {
    window.localStorage.removeItem('access_token');
    window.localStorage.removeItem('refresh_token');
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      accessToken:  null,
      refreshToken: null,
      user:         null,
      setAuth: (accessToken, refreshToken, user) => {
        syncCookies(accessToken, user.roles || []);
        syncPlainStorage(accessToken, refreshToken);
        set({ accessToken, refreshToken, user });
      },
      clearAuth: () => {
        syncCookies(null, []);
        syncPlainStorage(null, null);
        set({ accessToken: null, refreshToken: null, user: null });
      },
    }),
    { name: 'kohwai-auth' },
  ),
);
