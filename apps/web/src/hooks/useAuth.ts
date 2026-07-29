import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
export function useAuth(requiredRole?: 'validator' | 'admin' | 'ngo') {
  const router = useRouter();
  const { user, accessToken } = useAuthStore();
  useEffect(() => {
    if (!accessToken || !user) { router.push('/login'); return; }
    if (requiredRole && !user.roles.includes(requiredRole)) router.push('/dashboard');
  }, [accessToken, user, requiredRole, router]);
  return { user, isAuthenticated: !!accessToken };
}
