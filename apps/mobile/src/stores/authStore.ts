import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { UserProfile } from '@kohwai/shared/types';

interface AuthState {
  accessToken:  string | null;
  refreshToken: string | null;
  user:         UserProfile | null;
  setAuth: (access: string, refresh: string, user: UserProfile) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      accessToken: null, refreshToken: null, user: null,
      setAuth: (accessToken, refreshToken, user) => set({ accessToken, refreshToken, user }),
      clearAuth: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: 'kohwai-auth', storage: createJSONStorage(() => AsyncStorage) },
  ),
);
