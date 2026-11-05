import { useEffect, useState, useCallback } from 'react';
import { db } from '@/lib/db';
import { apiClient, isOfflineError } from '@/lib/api';
import { flushOutbox, outboxCounts } from '@/lib/offline';

type SyncStatus = 'idle' | 'syncing' | 'error' | 'offline';

export function useOfflineSync() {
  const [status, setStatus] = useState<SyncStatus>('idle');
  const [pendingCount, setPendingCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  const checkPending = useCallback(async () => {
    const [diag, box] = await Promise.all([db.diagnosisQueue.where('synced').equals(0).count(), outboxCounts()]);
    setPendingCount(diag + box.pending);
    setFailedCount(box.failed);
    return diag + box.pending;
  }, []);

  const sync = useCallback(async () => {
    setStatus('syncing');
    try {
      // 1. queued diagnoses (replayed one at a time — there is no bulk endpoint)
      const items = await db.diagnosisQueue.where('synced').equals(0).toArray();
      for (const item of items) {
        const path = item.kind === 'livestock' ? '/livestock/diagnose' : '/zunde/diagnose';
        const payload = item.kind === 'livestock'
          ? { animal_type_code: item.animalType, symptom_code: item.symptom }
          : { crop_type_code: item.cropType, symptom_code: item.symptom };
        await apiClient.post(path, payload);
        if (item.id !== undefined) await db.diagnosisQueue.update(item.id, { synced: 1 });
      }
      // 2. queued writes (borehole reports, listings)
      const res = await flushOutbox();
      await checkPending();
      setStatus(res.stillOffline ? 'offline' : res.failed ? 'error' : 'idle');
    } catch (e) {
      await checkPending();
      setStatus(isOfflineError(e) ? 'offline' : 'error');
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

  return { status, pendingCount, failedCount, sync };
}
