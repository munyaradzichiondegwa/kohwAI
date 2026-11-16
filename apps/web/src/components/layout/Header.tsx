'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';

type SyncStatus = 'online' | 'offline' | 'syncing';

type SyncInfo = { status: 'idle' | 'syncing' | 'error' | 'offline'; pendingCount: number; failedCount: number };

export default function Header({ title, sync }: { title?: string; sync?: SyncInfo } = {}) {
  const [status, setStatus] = useState<SyncStatus>('online');
  const user = useAuthStore(s => s.user);

  useEffect(() => {
    const update = () => setStatus(navigator.onLine ? 'online' : 'offline');
    window.addEventListener('online',  () => setStatus('online'));
    window.addEventListener('offline', () => setStatus('offline'));
    update();
  }, []);

  const statusConfig: Record<SyncStatus, { color: string; label: string }> = {
    online:  { color: 'bg-brand-green',  label: 'Online' },
    offline: { color: 'bg-brand-blue',   label: 'Offline' },
    syncing: { color: 'bg-brand-amber',  label: 'Syncing…' },
  };
  const effective: SyncStatus = sync?.status === 'syncing' ? 'syncing' : status;
  const s = statusConfig[effective];
  const pending = sync?.pendingCount ?? 0;

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🌿</span>
        <span className="font-bold text-brand-green text-lg">{title || 'KohwAI'}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full text-white ${s.color}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-white opacity-80" />
          {s.label}{pending > 0 ? ` · ${pending} waiting` : ''}
        </span>
        {(sync?.failedCount ?? 0) > 0 && <span title="Some saved items were rejected by the server" className="text-xs text-brand-red">⚠ {sync!.failedCount}</span>}
        <Link href="/account" aria-label="My account" className="relative">
          <span className="text-xl">👤</span>
        </Link>
      </div>
    </header>
  );
}
