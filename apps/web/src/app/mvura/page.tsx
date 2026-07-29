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
  const { data: boreholes = [] } = useSWR('boreholes-' + (district || 'all'), () => getBoreholes(district));
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function submitReport(status: string) {
    if (!selected) return;
    setSubmitting(true);
    await reportBorehole({ id: selected, status: status as any });
    mutate('boreholes-' + (district || 'all'));
    setSubmitting(false);
    setDone(true);
    setTimeout(() => { setDone(false); setSelected(null); }, 1500);
  }

  return (
    <AppShell title="Mvura — Water">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">💧 Water points near you</h1>
        <p className="text-sm text-gray-500 mt-1">
          Community-reported status. Tap a borehole below to update it after visiting.
        </p>
      </section>

      <section className="mb-6">
        <BoreholeMap district={district} />
      </section>

      <section>
        <h2 className="font-semibold text-gray-800 mb-2">Report a status update</h2>
        {!selected && (
          <div className="flex flex-col gap-2">
            {boreholes.map((bh: any) => (
              <button key={bh.id} onClick={() => setSelected(bh.id)}
                className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center text-left">
                <div>
                  <p className="font-medium text-sm text-gray-900">{bh.name}</p>
                  <p className="text-xs text-gray-500">{bh.village}</p>
                </div>
                <span className="text-xs text-brand-green font-medium">Update →</span>
              </button>
            ))}
          </div>
        )}
        {selected && !done && (
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
        {done && (
          <div className="bg-brand-green/10 border border-brand-green/30 rounded-xl p-4 text-center text-brand-green font-medium">
            Thanks — status recorded ✓
          </div>
        )}
      </section>
    </AppShell>
  );
}
