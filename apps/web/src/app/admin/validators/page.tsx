'use client';
import { useEffect, useState, useCallback } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { DISTRICTS } from '@kohwai/shared/constants';

export default function AdminValidatorsPage() {
  const [validators, setValidators] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [phone, setPhone] = useState('');
  const [districts, setDistricts] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    apiClient.get('/community/validators').then(r => setValidators(r.data)).catch(e => setError(e?.detail || 'Could not load validators.'));
  }, []);
  useEffect(load, [load]);

  const toggle = (d: string) => setDistricts(cur => cur.includes(d) ? cur.filter(x => x !== d) : [...cur, d]);

  async function appoint() {
    setBusy(true); setMsg(null);
    try {
      await apiClient.post('/community/validators', { phone: phone.trim(), districts });
      setMsg('Validator appointed ✓'); setPhone(''); setDistricts([]); load();
    } catch (e: any) { setMsg(e?.detail || 'Could not appoint this validator.'); }
    setBusy(false);
  }

  async function revoke(id: string) {
    if (!confirm('Remove this person\'s validator access?')) return;
    try { await apiClient.delete(`/community/validators/${id}`); load(); }
    catch (e: any) { setMsg(e?.detail || 'Could not remove access.'); }
  }

  return (
    <AppShell title="Validators">
      <h1 className="text-xl font-bold text-gray-900 mb-2">👥 Validators &amp; admins</h1>
      <p className="text-sm text-gray-500 mb-4">
        A validator only sees and decides reports from the districts assigned here, and can never review their own reports.
        The person must already have a KohwAI account.
      </p>

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">
        <h2 className="font-semibold text-gray-800 mb-2 text-sm">Appoint a validator</h2>
        <input value={phone} onChange={e => setPhone(e.target.value)} inputMode="tel" placeholder="Phone, e.g. 0771234567"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-2" />
        <div className="flex flex-wrap gap-1.5 mb-3">
          {DISTRICTS.map(d => (
            <button key={d} onClick={() => toggle(d)} type="button"
              className={`px-2.5 py-1 rounded-full text-xs border ${districts.includes(d) ? 'bg-brand-green text-white border-brand-green' : 'border-gray-300 text-gray-600'}`}>{d}</button>
          ))}
        </div>
        {msg && <p className="text-xs text-gray-600 mb-2">{msg}</p>}
        <button onClick={appoint} disabled={busy || !phone || !districts.length}
          className="w-full bg-brand-green text-white rounded-xl py-2 text-sm font-medium disabled:opacity-50">Appoint</button>
      </section>

      {error && <p className="text-sm text-brand-red">{error}</p>}
      <div className="flex flex-col gap-2">
        {validators.map(v => (
          <div key={v.id} className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-gray-900">{v.phone}</p>
              <p className="text-xs text-gray-500">
                {v.roles.join(', ')} · {v.roles.includes('admin') && !v.districts?.length ? 'all districts' : (v.districts?.join(', ') || 'no districts assigned')}
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold text-brand-green block">{v.reports_reviewed} reviewed</span>
              {!v.roles.includes('admin') && <button onClick={() => revoke(v.id)} className="text-xs text-brand-red mt-1">Remove</button>}
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
