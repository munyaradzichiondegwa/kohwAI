import { useEffect, useState, useCallback } from 'react';
import { db } from '@/lib/db';
import { apiClient } from '@/lib/api';

type SyncStatus = 'idle' | 'syncing' | 'error' | 'offline';

export function useOfflineSync() {
  const [status, setStatus]             = useState<SyncStatus>('idle');
  const [pendingCount, setPendingCount] = useState(0);

  const checkPending = useCallback(async () => {
    const c = await db.diagnosisQueue.where('synced').equals(0 as any).count();
    setPendingCount(c);
    return c;
  }, []);

  const sync = useCallback(async () => {
    setStatus('syncing');
    try {
      const items = await db.diagnosisQueue.where('synced').equals(0 as any).toArray();
      for (const item of items) {
        // Route each queued diagnosis to the endpoint matching its kind —
        // there is no combined bulk-queue endpoint, so replay one at a time.
        const path = item.kind === 'livestock' ? '/livestock/diagnose' : '/zunde/diagnose';
        const payload = item.kind === 'livestock'
          ? { animal_type_code: item.animalType, symptom_code: item.symptom }
          : { crop_type_code: item.cropType, symptom_code: item.symptom };
        await apiClient.post(path, payload);
        if (item.id !== undefined) await db.diagnosisQueue.update(item.id, { synced: true });
      }
      await checkPending();
      setStatus('idle');
    } catch {
      setStatus('error');
    }
  }, [checkPending]);

  useEffect(() => {
    checkPending().then(c => { if (navigator.onLine && c > 0) sync(); });
    const handleOnline = () => sync();
    const handleOffline = () => setStatus('offline');
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checkPending, sync]);

  return { status, pendingCount };
}
