'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { getListings, addListing } from '@/lib/offline';
import { useAuthStore } from '@/stores/authStore';
import useSWR, { mutate } from 'swr';

const TYPES = [
  { value: 'seed', label: '🌱 Seed', color: 'bg-brand-green/10 text-brand-green' },
  { value: 'produce', label: '🥬 Produce', color: 'bg-brand-amber/10 text-brand-amber' },
  { value: 'livestock', label: '🐄 Livestock', color: 'bg-brand-blue/10 text-brand-blue' },
  { value: 'input', label: '🧰 Farm inputs', color: 'bg-gray-100 text-gray-700' },
] as const;

export default function MusikaPage() {
  const user = useAuthStore(s => s.user);
  const [filter, setFilter] = useState<string | null>(null);
  const { data: listings = [] } = useSWR('listings-' + (filter || 'all'), () => getListings(filter as any));
  const [showForm, setShowForm] = useState(false);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [showInsurance, setShowInsurance] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    apiClient.get('/musika/insurance/my-enrollment').then(r => setEnrollment(r.data)).catch(() => {});
  }, []);

  async function enrollInsurance() {
    setEnrolling(true);
    try {
      const res = await apiClient.post('/musika/insurance/enroll', {
        district: user?.district || 'Harare', season: '2026-27', ecocash_number: user?.phone,
      });
      setEnrollment(res.data);
    } catch { /* requires a network connection — this isn't an offline-capable feature since it's a real record */ }
    setEnrolling(false);
  }
  const [form, setForm] = useState({ type: 'seed', title: '', quantity: '', unit: 'kg', priceUsd: '' });
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!form.title || !form.quantity || !form.priceUsd) return;
    setSubmitting(true);
    await addListing({
      type: form.type as any, title: form.title, description: '',
      quantity: Number(form.quantity), unit: form.unit, priceUsd: Number(form.priceUsd),
      district: user?.district || 'Harare', sellerPhone: user?.phone || '',
      expiresAt: new Date(Date.now() + 14 * 86400000).toISOString(),
    });
    mutate('listings-' + (filter || 'all'));
    setSubmitting(false); setShowForm(false);
    setForm({ type: 'seed', title: '', quantity: '', unit: 'kg', priceUsd: '' });
  }

  return (
    <AppShell title="Musika — Marketplace">
      <section className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">🛒 Marketplace</h1>
        <button onClick={() => setShowForm(v => !v)} className="text-sm bg-brand-green text-white rounded-lg px-3 py-1.5 font-medium">
          + Sell something
        </button>
      </section>

      <section className="mb-6">
        <button onClick={() => setShowInsurance(v => !v)} className="text-sm text-brand-green font-medium mb-2">
          🌦️ {enrollment ? 'Drought insurance: enrolled ✓' : 'Drought insurance — tap to enroll'}
        </button>
        {showInsurance && (
          <div className="bg-white rounded-2xl border border-gray-100 p-4">
            {enrollment ? (
              <div className="text-sm text-gray-700">
                <p>Enrolled for <strong>{enrollment.season}</strong> in {enrollment.district}.</p>
                <p className="mt-1">Payout if triggered: <strong>${enrollment.payout_amount_usd}</strong></p>
                <p className="text-xs text-gray-400 mt-2">
                  This is a real enrollment record. Payouts are triggered from satellite rainfall data, but
                  actual disbursement is recorded manually until EcoCash merchant integration is connected —
                  it is not automatic yet.
                </p>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-700 mb-3">
                  Free parametric drought cover for the 2026-27 season. If satellite rainfall data shows a
                  severe deficit in your district, you're queued for a payout — no claims paperwork needed.
                </p>
                <button onClick={enrollInsurance} disabled={enrolling}
                  className="w-full bg-brand-green text-white rounded-xl py-2.5 text-sm font-medium disabled:opacity-50">
                  {enrolling ? 'Enrolling…' : 'Enroll now'}
                </button>
              </>
            )}
          </div>
        )}
      </section>

      {showForm && (
        <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">
          <div className="grid grid-cols-2 gap-2 mb-3">
            {TYPES.map(t => (
              <button key={t.value} onClick={() => setForm(f => ({ ...f, type: t.value }))}
                className={`p-2 rounded-lg text-sm font-medium ${form.type === t.value ? t.color + ' ring-2 ring-offset-1 ring-brand-green' : 'bg-gray-50 text-gray-600'}`}>
                {t.label}
              </button>
            ))}
          </div>
          <input placeholder="What are you selling?" value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-2" />
          <div className="grid grid-cols-3 gap-2 mb-3">
            <input placeholder="Qty" type="number" value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Unit (kg)" value={form.unit}
              onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Price USD" type="number" value={form.priceUsd}
              onChange={e => setForm(f => ({ ...f, priceUsd: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <button onClick={submit} disabled={submitting}
            className="w-full bg-brand-green text-white rounded-xl py-2.5 text-sm font-medium disabled:opacity-50">
            {submitting ? 'Posting…' : 'Post listing'}
          </button>
        </section>
      )}

      <section className="mb-4 flex gap-2 overflow-x-auto">
        <button onClick={() => setFilter(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${!filter ? 'bg-brand-green text-white' : 'bg-gray-100 text-gray-600'}`}>
          All
        </button>
        {TYPES.map(t => (
          <button key={t.value} onClick={() => setFilter(t.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${filter === t.value ? 'bg-brand-green text-white' : 'bg-gray-100 text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </section>

      <section className="flex flex-col gap-2">
        {listings.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No listings yet.</p>}
        {listings.map((l: any) => (
          <div key={l.id} className="bg-white rounded-xl border border-gray-100 p-3">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-gray-900">{l.title}</p>
                <p className="text-xs text-gray-500">{l.quantity} {l.unit} · {l.district}</p>
              </div>
              <p className="font-bold text-brand-green">${l.priceUsd}</p>
            </div>
            {l.sellerPhone && <p className="text-xs text-gray-400 mt-2">Contact: {l.sellerPhone}</p>}
          </div>
        ))}
      </section>
    </AppShell>
  );
}
