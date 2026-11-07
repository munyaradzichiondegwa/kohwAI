'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { toCamel } from '@/lib/case';
import { useAuthStore } from '@/stores/authStore';
import { DISTRICTS } from '@kohwai/shared/constants';

export default function AccountPage() {
  const router = useRouter();
  const { user, accessToken, refreshToken, setAuth, clearAuth } = useAuthStore();
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [pin, setPin] = useState(''); const [pin2, setPin2] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const say = (ok: boolean, text: string) => setMsg({ ok, text });
  const fail = (e: any) => say(false, e?.offline ? 'You need a connection for this.' : (e?.detail || 'Something went wrong.'));
  const merge = (data: any) => { if (user && accessToken) setAuth(accessToken, refreshToken || '', { ...user, ...toCamel(data) }); };

  async function update(body: Record<string, unknown>, okText: string) {
    try { merge((await apiClient.patch('/auth/me', body)).data); say(true, okText); } catch (e) { fail(e); }
  }

  async function savePin() {
    if (pin !== pin2) return say(false, 'The two PINs do not match.');
    try {
      await apiClient.put('/auth/me/pin', { pin });
      merge({ has_pin: true }); setPin(''); setPin2('');
      say(true, 'PIN saved. Use it when you dial the USSD service.');
    } catch (e) { fail(e); }
  }

  async function download() {
    try {
      const res = await apiClient.get('/auth/me/export');
      const url = URL.createObjectURL(new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' }));
      const a = document.createElement('a'); a.href = url; a.download = 'my-kohwai-data.json'; a.click(); URL.revokeObjectURL(url);
      say(true, 'Your data has been downloaded.');
    } catch (e) { fail(e); }
  }

  async function deleteAccount() {
    try {
      await apiClient.post('/auth/me/delete-account', { confirm: true });
      clearAuth(); router.replace('/login');
    } catch (e) { fail(e); setConfirmDelete(false); }
  }

  return (
    <AppShell title="My account">
      <p className="text-sm text-gray-500 mb-4">{user?.phone}</p>
      {msg && <div className={`rounded-xl p-3 mb-4 text-sm ${msg.ok ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-red/10 text-brand-red'}`}>{msg.text}</div>}

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
        <h2 className="font-semibold text-gray-800 mb-2">District</h2>
        <select value={user?.district || ''} onChange={e => update({ district: e.target.value }, 'District updated.')}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="" disabled>Select…</option>
          {DISTRICTS.map(d => <option key={d}>{d}</option>)}
        </select>
        <p className="text-xs text-gray-400 mt-1">Alerts, boreholes and listings follow your district.</p>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
        <label className="flex items-center justify-between">
          <span><span className="font-semibold text-gray-800 block">SMS alerts</span>
            <span className="text-xs text-gray-500">Urgent warnings for your district (at most a few a day).</span></span>
          <input type="checkbox" checked={user?.smsAlerts !== false}
            onChange={e => update({ sms_alerts: e.target.checked }, e.target.checked ? 'SMS alerts are ON.' : 'SMS alerts are OFF.')} className="w-5 h-5" />
        </label>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
        <h2 className="font-semibold text-gray-800 mb-1">{user?.hasPin ? 'Change your PIN' : 'Set a PIN'}</h2>
        <p className="text-xs text-gray-500 mb-2">A 4-digit PIN protects your reports and details when you use KohwAI by USSD. Also use this if you forgot or locked your PIN.</p>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <input type="password" inputMode="numeric" maxLength={4} placeholder="New PIN" value={pin} onChange={e => setPin(e.target.value.replace(/\D/g, ''))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-center tracking-widest" />
          <input type="password" inputMode="numeric" maxLength={4} placeholder="Repeat PIN" value={pin2} onChange={e => setPin2(e.target.value.replace(/\D/g, ''))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-center tracking-widest" />
        </div>
        <button onClick={savePin} disabled={pin.length !== 4 || pin2.length !== 4}
          className="w-full bg-brand-green text-white rounded-xl py-2 text-sm font-medium disabled:opacity-50">Save PIN</button>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
        <h2 className="font-semibold text-gray-800 mb-2">Your data</h2>
        <button onClick={download} className="w-full border border-gray-300 rounded-xl py-2 text-sm mb-2">Download my data</button>
        {!confirmDelete ? (
          <button onClick={() => setConfirmDelete(true)} className="w-full text-sm text-brand-red py-2">Delete my account…</button>
        ) : (
          <div className="bg-brand-red/5 rounded-xl p-3">
            <p className="text-sm text-gray-700 mb-2">This permanently deletes your animals, listings and personal details. It cannot be undone.</p>
            <div className="flex gap-2">
              <button onClick={deleteAccount} className="flex-1 bg-brand-red text-white rounded-lg py-2 text-sm font-medium">Yes, delete</button>
              <button onClick={() => setConfirmDelete(false)} className="flex-1 border border-gray-300 rounded-lg py-2 text-sm">Cancel</button>
            </div>
          </div>
        )}
      </section>

      <button onClick={() => { clearAuth(); router.replace('/login'); }} className="w-full text-sm text-gray-500 py-2">Log out</button>
    </AppShell>
  );
}
