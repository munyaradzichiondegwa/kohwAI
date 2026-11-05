'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { getListings, addListing } from '@/lib/offline';
import { currentSeason } from '@/lib/season';
import { useAuthStore } from '@/stores/authStore';
import useSWR, { mutate } from 'swr';

const TYPES = [
  { value: 'seed', label: '🌱 Seed', color: 'bg-brand-green/10 text-brand-green' },
  { value: 'produce', label: '🥬 Produce', color: 'bg-brand-amber/10 text-brand-amber' },
  { value: 'livestock', label: '🐄 Livestock', color: 'bg-brand-blue/10 text-brand-blue' },
  { value: 'input', label: '🧰 Farm inputs', color: 'bg-gray-100 text-gray-700' },
] as const;

type Notice = { kind: 'ok' | 'queued' | 'error'; text: string };
const noticeClass = (k: Notice['kind']) =>
  k === 'error' ? 'bg-brand-red/10 text-brand-red' : k === 'queued' ? 'bg-brand-blue/10 text-brand-blue' : 'bg-brand-green/10 text-brand-green';

export default function MusikaPage() {
  const user = useAuthStore(s => s.user);
  const [filter, setFilter] = useState<string | null>(null);
  const listKey = 'listings-' + (filter || 'all');
  const { data: result, error: loadError } = useSWR(listKey, () => getListings((filter as any) ?? undefined));
  const listings = result?.data ?? [];
  const [showForm, setShowForm] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  // ── insurance (a real record: needs a connection, and is only offered when the admin has opened enrolment)
  const [insuranceOpen, setInsuranceOpen] = useState(false);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [showInsurance, setShowInsurance] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [insuranceMsg, setInsuranceMsg] = useState<string | null>(null);
  const [ecocash, setEcocash] = useState(user?.phone || '');

  useEffect(() => {
    apiClient.get('/settings').then(r => {
      const flags = (r.data as any[]).find(s => s.key === 'feature_flags')?.value || {};
      setInsuranceOpen(!!flags.musika_insurance_enrollment);
    }).catch(() => {});
    apiClient.get('/musika/insurance/my-enrollment').then(r => setEnrollment(r.data)).catch(() => {});
  }, []);

  async function enrollInsurance() {
    if (!user?.district) { setInsuranceMsg('Set your district in your profile first.'); return; }
    setEnrolling(true); setInsuranceMsg(null);
    try {
      const res = await apiClient.post('/musika/insurance/enroll', {
        district: user.district, season: currentSeason(), ecocash_number: ecocash || null,
      });
      setEnrollment(res.data);
    } catch (e: any) {
      setInsuranceMsg(e?.offline ? 'Enrolment needs a connection. Please try again when you have signal.' : (e?.detail || 'Could not enrol.'));
    }
    setEnrolling(false);
  }

  // ── listing form
  const [form, setForm] = useState({ type: 'seed', title: '', quantity: '', unit: 'kg', priceUsd: '', sharePhone: false });
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!form.title || !form.quantity || !form.priceUsd) { setNotice({ kind: 'error', text: 'Please fill in what, how many and the price.' }); return; }
    if (!user?.district) { setNotice({ kind: 'error', text: 'Set your district in your profile first.' }); return; }
    setSubmitting(true); setNotice(null);
    try {
      const out = await addListing({
        type: form.type as any, title: form.title.trim(), quantity: Number(form.quantity), unit: form.unit.trim(),
        priceUsd: Number(form.priceUsd), district: user.district, sharePhone: form.sharePhone,
      });
      setNotice(out.status === 'sent'
        ? { kind: 'ok', text: 'Your listing is live for 30 days.' }
        : { kind: 'queued', text: 'No signal: your listing is saved on this phone and will be posted automatically when you are back online.' });
      mutate(listKey);
      setShowForm(false);
      setForm({ type: 'seed', title: '', quantity: '', unit: 'kg', priceUsd: '', sharePhone: false });
    } catch (e: any) {
      setNotice({ kind: 'error', text: e?.detail || 'Could not post your listing.' });
    } finally { setSubmitting(false); }
  }

  async function remove(id: string) {
    try { await apiClient.delete(`/musika/listings/${id}`); mutate(listKey); }
    catch (e: any) { setNotice({ kind: 'error', text: e?.detail || 'Could not remove the listing.' }); }
  }

  return (
    <AppShell title="Musika — Marketplace">
      <section className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">🛒 Marketplace</h1>
        <button onClick={() => setShowForm(v => !v)} className="text-sm bg-brand-green text-white rounded-lg px-3 py-1.5 font-medium">
          + Sell something
        </button>
      </section>

      {notice && <div className={`rounded-xl p-3 mb-4 text-sm ${noticeClass(notice.kind)}`}>{notice.text}</div>}
      {result?.source === 'cache' && (
        <p className="text-xs bg-brand-blue/10 text-brand-blue rounded-lg px-3 py-2 mb-4">
          You are offline — showing the last saved listings{result.cachedAt ? ` (${new Date(result.cachedAt).toLocaleString()})` : ''}.
        </p>
      )}
      {result?.source === 'demo' && <p className="text-xs bg-brand-amber/20 rounded-lg px-3 py-2 mb-4">DEMO DATA — not real listings.</p>}
      {loadError && <p className="text-xs text-brand-red mb-4">Could not load listings: {(loadError as any)?.detail || 'please try again.'}</p>}

      {(insuranceOpen || enrollment) && (
        <section className="mb-6">
          <button onClick={() => setShowInsurance(v => !v)} className="text-sm text-brand-green font-medium mb-2">
            🌦️ {enrollment ? `Drought cover: enrolled for ${enrollment.season} ✓` : 'Drought cover — tap for details'}
          </button>
          {showInsurance && (
            <div className="bg-white rounded-2xl border border-gray-100 p-4">
              {enrollment ? (
                <div className="text-sm text-gray-700">
                  <p>Enrolled for <strong>{enrollment.season}</strong> in {enrollment.district}.</p>
                  <p className="mt-1">Payout if triggered: <strong>${enrollment.payout_amount_usd}</strong></p>
                  <p className="text-xs text-gray-400 mt-2">
                    A payout is created only if satellite rainfall stays in severe deficit for several days in a row during the Nov–Mar
                    season, and you enrolled at least two weeks before the dry spell began. Money is sent manually by our team after
                    a payout is approved — it is not automatic yet.
                  </p>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-700 mb-3">
                    Pilot drought cover for the {currentSeason()} season in {user?.district || 'your district'}. If satellite data shows a
                    prolonged rainfall deficit, a payout is queued — no claim forms.
                  </p>
                  <label className="text-xs text-gray-500">EcoCash number for payouts</label>
                  <input value={ecocash} onChange={e => setEcocash(e.target.value)} inputMode="tel"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3" />
                  {insuranceMsg && <p className="text-xs text-brand-red mb-2">{insuranceMsg}</p>}
                  <button onClick={enrollInsurance} disabled={enrolling}
                    className="w-full bg-brand-green text-white rounded-xl py-2.5 text-sm font-medium disabled:opacity-50">
                    {enrolling ? 'Enrolling…' : 'Enrol now'}
                  </button>
                </>
              )}
            </div>
          )}
        </section>
      )}

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
            <input placeholder="Qty" type="number" min="0" value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Unit (kg)" value={form.unit}
              onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Price USD" type="number" min="0" value={form.priceUsd}
              onChange={e => setForm(f => ({ ...f, priceUsd: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <label className="flex items-start gap-2 text-xs text-gray-600 mb-3">
            <input type="checkbox" checked={form.sharePhone} onChange={e => setForm(f => ({ ...f, sharePhone: e.target.checked }))} className="mt-0.5" />
            Show my phone number to buyers. (Left unticked, your number stays private.)
          </label>
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
        {listings.map(l => (
          <div key={l.id} className="bg-white rounded-xl border border-gray-100 p-3">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-gray-900">{l.title}</p>
                <p className="text-xs text-gray-500">{l.quantity} {l.unit} · {l.district}</p>
              </div>
              <p className="font-bold text-brand-green">${l.priceUsd}</p>
            </div>
            {l.sellerPhone && <p className="text-xs text-gray-500 mt-2">Contact: {l.sellerPhone}</p>}
            {l.isMine && (
              <button onClick={() => remove(l.id)} className="text-xs text-brand-red mt-2">Remove my listing</button>
            )}
          </div>
        ))}
      </section>
    </AppShell>
  );
}
