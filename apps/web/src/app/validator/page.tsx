'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function ValidatorPage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await apiClient.get('/community/queue');
      setQueue(res.data);
    } catch (e: any) {
      setError(e?.status === 403 || e?.detail?.includes('required')
        ? 'You need validator access for this page.'
        : 'Could not load the queue — check your connection.');
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function decide(item: any, approve: boolean) {
    setBusyId(item.id);
    try {
      if (approve) {
        await apiClient.post(`/community/queue/${item.kind}/${item.id}/approve`);
      } else {
        await apiClient.post(`/community/queue/${item.kind}/${item.id}/reject`, { reason: 'Rejected by validator' });
      }
      setQueue(q => q.filter(x => x.id !== item.id));
    } catch { /* leave item in the queue so the validator can retry */ }
    finally { setBusyId(null); }
  }

  const KIND_LABEL: Record<string, string> = {
    pest_sighting: '🐛 Pest sighting', borehole_report: '💧 Borehole report', community_report: '📋 Report',
  };

  return (
    <AppShell title="Validator Queue">
      <section className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">✅ Community validation queue</h1>
        <p className="text-sm text-gray-500 mt-1">Review reports submitted by farmers before they go live.</p>
      </section>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-brand-red">{error}</p>}
      {!loading && !error && queue.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">Queue is empty — nothing pending. 🎉</p>
      )}

      <div className="flex flex-col gap-2">
        {queue.map(item => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-100 p-3">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-medium text-gray-500">{KIND_LABEL[item.kind] || item.kind}</span>
              <span className="text-xs text-gray-400">{item.district}</span>
            </div>
            <p className="text-sm text-gray-900 mb-1">{item.summary}</p>
            {item.reporter_phone && <p className="text-xs text-gray-400 mb-3">From: {item.reporter_phone}</p>}
            <div className="flex gap-2">
              <button disabled={busyId === item.id} onClick={() => decide(item, true)}
                className="flex-1 bg-brand-green text-white rounded-lg py-1.5 text-sm font-medium disabled:opacity-50">
                Approve
              </button>
              <button disabled={busyId === item.id} onClick={() => decide(item, false)}
                className="flex-1 bg-brand-red text-white rounded-lg py-1.5 text-sm font-medium disabled:opacity-50">
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
