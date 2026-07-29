'use client';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';

type SyncStatus = 'online' | 'offline' | 'syncing';

export default function Header({ title }: { title?: string } = {}) {
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
  const s = statusConfig[status];

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🌿</span>
        <span className="font-bold text-brand-green text-lg">{title || 'KohwAI'}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full text-white ${s.color}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-white opacity-80" />
          {s.label}
        </span>
        <button aria-label="Notifications" className="relative">
          <span className="text-xl">🔔</span>
        </button>
      </div>
    </header>
  );
}
