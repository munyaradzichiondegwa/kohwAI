'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from './Header';
import BottomNav from './BottomNav';
import { apiClient } from '@/lib/api';
import { toCamel } from '@/lib/case';
import { useAuthStore } from '@/stores/authStore';
import { useOfflineSync } from '@/hooks/useOfflineSync';

export default function AppShell({ title, children }: { title?: string; children: React.ReactNode }) {
  const router = useRouter();
  const { user, accessToken, refreshToken, setAuth } = useAuthStore();
  const sync = useOfflineSync();     // mounted here so queued diagnoses / reports / listings are actually sent when signal returns

  // Refresh the profile once per visit: picks up consent/PIN/preferences changed elsewhere (e.g. on USSD).
  useEffect(() => {
    if (!accessToken || accessToken.startsWith('local-')) return;
    apiClient.get('/auth/me').then(r => {
      if (user) setAuth(accessToken, refreshToken || '', { ...user, ...toCamel(r.data) });
      if (r.data.needs_consent) router.replace('/consent');
    }).catch(() => { /* offline or expired: keep working with the saved profile */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  return (
    <div className="flex flex-col min-h-screen">
      <Header title={title} sync={sync} />
      <main className="flex-1 px-4 py-4 pb-24 max-w-2xl mx-auto w-full">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
