'use client';
import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import BoreholeMap from '@/components/maps/BoreholeMap';
import { getBoreholes, reportBorehole } from '@/lib/offline';
import { useAuthStore } from '@/stores/authStore';
import useSWR, { mutate } from 'swr';

const STATUS_OPTIONS = [
  { value: 'working', label: 'Working normally', color: 'bg-brand-green' },
  { value: 'low',     label: 'Low water / slow',  color: 'bg-brand-amber' },
  { value: 'dry',     label: 'Dry',                color: 'bg-brand-red' },
  { value: 'broken',  label: 'Broken / pump fault', color: 'bg-gray-500' },
] as const;

export default function MvuraPage() {
  const user = useAuthStore(s => s.user);
  const district = user?.district;
  const key = 'boreholes-' + (district || 'all');
  const { data: result, error: loadError } = useSWR(key, () => getBoreholes(district));
  const boreholes = result?.data ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState<{ kind: 'ok' | 'queued' | 'error'; text: string } | null>(null);

  async function submitReport(status: (typeof STATUS_OPTIONS)[number]['value']) {
    if (!selected) return;
    setSubmitting(true);
    try {
      const out = await reportBorehole({ id: selected, status });
      setNotice(out.status === 'sent'
        ? { kind: 'ok', text: 'Report sent. It shows as unverified until a community validator confirms it.' }
        : { kind: 'queued', text: 'No signal: your report is saved on this phone and will be sent automatically when you are back online.' });
      mutate(key);
      setSelected(null);
    } catch (e: any) {
      setNotice({ kind: 'error', text: e?.detail || 'Could not send your report. Please try again.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Mvura — Water">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">💧 Water points near you</h1>
        <p className="text-sm text-gray-500 mt-1">
          Status shown is the last one confirmed by a validator. Reports from farmers are marked <em>unverified</em> until confirmed.
        </p>
        {result?.source === 'cache' && (
          <p className="text-xs bg-brand-blue/10 text-brand-blue rounded-lg px-3 py-2 mt-2">
            You are offline — showing the last saved list{result.cachedAt ? ` (${new Date(result.cachedAt).toLocaleString()})` : ''}.
          </p>
        )}
        {result?.source === 'demo' && <p className="text-xs bg-brand-amber/20 rounded-lg px-3 py-2 mt-2">DEMO DATA — not real boreholes.</p>}
        {loadError && <p className="text-xs text-brand-red mt-2">Could not load boreholes: {(loadError as any)?.detail || 'please try again.'}</p>}
      </section>

      <section className="mb-6">
        <BoreholeMap district={district} />
      </section>

      <section>
        <h2 className="font-semibold text-gray-800 mb-2">Report a status update</h2>
        {notice && (
          <div className={`rounded-xl p-3 mb-3 text-sm ${notice.kind === 'error' ? 'bg-brand-red/10 text-brand-red' : notice.kind === 'queued' ? 'bg-brand-blue/10 text-brand-blue' : 'bg-brand-green/10 text-brand-green'}`}>
            {notice.text}
          </div>
        )}
        {!selected && (
          <div className="flex flex-col gap-2">
            {!boreholes.length && <p className="text-sm text-gray-400 text-center py-4">No boreholes registered yet.</p>}
            {boreholes.map(bh => (
              <button key={bh.id} onClick={() => { setSelected(bh.id); setNotice(null); }}
                className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center text-left">
                <div>
                  <p className="font-medium text-sm text-gray-900">{bh.name}</p>
                  <p className="text-xs text-gray-500">
                    {bh.village} · {bh.status}{bh.verified ? '' : ' (never verified)'}
                    {bh.pendingReport && <span className="text-brand-amber"> · unverified report: {bh.pendingReport}</span>}
                  </p>
                </div>
                <span className="text-xs text-brand-green font-medium">Update →</span>
              </button>
            ))}
          </div>
        )}
        {selected && (
          <div className="bg-white rounded-2xl border border-gray-100 p-4">
            <p className="text-sm font-medium text-gray-800 mb-3">Current status:</p>
            <div className="grid grid-cols-2 gap-2">
              {STATUS_OPTIONS.map(o => (
                <button key={o.value} disabled={submitting} onClick={() => submitReport(o.value)}
                  className={`${o.color} text-white rounded-xl py-3 text-sm font-medium disabled:opacity-50`}>
                  {o.label}
                </button>
              ))}
            </div>
            <button onClick={() => setSelected(null)} className="mt-3 w-full text-sm text-gray-500">Cancel</button>
          </div>
        )}
      </section>
    </AppShell>
  );
}
