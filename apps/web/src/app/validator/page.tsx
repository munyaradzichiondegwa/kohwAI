'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function ValidatorPage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<any | null>(null);
  const [reason, setReason] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const REASONS = ['I could not confirm this on the ground', 'Looks like a duplicate report', 'Wrong district or location', 'Information is unclear or incomplete'];

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

  async function decide(item: any, approve: boolean, why?: string) {
    setBusyId(item.id); setActionError(null);
    try {
      if (approve) {
        await apiClient.post(`/community/queue/${item.kind}/${item.id}/approve`);
      } else {
        await apiClient.post(`/community/queue/${item.kind}/${item.id}/reject`, { reason: why });
      }
      setQueue(q => q.filter(x => x.id !== item.id));
      setRejecting(null); setReason('');
    } catch (e: any) {
      // e.g. 403 "cannot review your own submission", 409 "already approved" — say so instead of failing silently
      setActionError(e?.detail || 'Could not save your decision. Please try again.');
      if (e?.status === 409 || e?.status === 404) setQueue(q => q.filter(x => x.id !== item.id));
    }
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
      {actionError && <p className="text-sm text-brand-red mb-2">{actionError}</p>}
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
            {rejecting?.id === item.id ? (
              <div className="mb-1">
                <p className="text-xs font-medium text-gray-700 mb-1">Why is this rejected? (the farmer is told)</p>
                <div className="flex flex-col gap-1 mb-2">
                  {REASONS.map(r => (
                    <button key={r} onClick={() => setReason(r)}
                      className={`text-left text-xs rounded-lg border px-2 py-1.5 ${reason === r ? 'border-brand-red bg-brand-red/5' : 'border-gray-200'}`}>{r}</button>
                  ))}
                </div>
                <input value={REASONS.includes(reason) ? '' : reason} onChange={e => setReason(e.target.value)} placeholder="…or type your own reason"
                  className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs mb-2" />
                <div className="flex gap-2">
                  <button disabled={busyId === item.id || reason.trim().length < 5} onClick={() => decide(item, false, reason.trim())}
                    className="flex-1 bg-brand-red text-white rounded-lg py-1.5 text-sm font-medium disabled:opacity-50">Confirm rejection</button>
                  <button onClick={() => { setRejecting(null); setReason(''); }} className="flex-1 border border-gray-300 rounded-lg py-1.5 text-sm">Cancel</button>
                </div>
              </div>
            ) : (
            <div className="flex gap-2">
              <button disabled={busyId === item.id} onClick={() => decide(item, true)}
                className="flex-1 bg-brand-green text-white rounded-lg py-1.5 text-sm font-medium disabled:opacity-50">
                Approve
              </button>
              <button disabled={busyId === item.id} onClick={() => { setRejecting(item); setReason(''); setActionError(null); }}
                className="flex-1 bg-brand-red text-white rounded-lg py-1.5 text-sm font-medium disabled:opacity-50">
                Reject
              </button>
            </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
