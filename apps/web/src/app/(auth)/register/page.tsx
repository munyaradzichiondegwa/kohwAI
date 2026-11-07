'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { toCamel } from '@/lib/case';
import ConsentSummary from '@/components/ui/ConsentSummary';
import { useAuthStore } from '@/stores/authStore';
import { DISTRICTS } from '@kohwai/shared/constants';

export default function RegisterPage() {
  const router  = useRouter();
  const setAuth = useAuthStore(s => s.setAuth);
  const [step, setStep]       = useState<'form'|'otp'>('form');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [form, setForm]       = useState({ phone:'', district:'', language:'en' });
  const [otp, setOtp]         = useState('');

  const [accepted, setAccepted] = useState(false);

  async function requestOtp() {
    setLoading(true); setError('');
    try { await apiClient.post('/auth/otp/request', { phone: form.phone }); setStep('otp'); }
    catch (e: any) {
      setError(e?.offline ? 'You need a connection to create an account. Please try again when you have signal.' : (e?.detail || 'Could not send the code.'));
    }
    finally { setLoading(false); }
  }
  async function verify() {
    setLoading(true); setError('');
    try {
      const res = await apiClient.post('/auth/otp/verify', { ...form, otp, accept_terms: accepted });
      setAuth(res.data.access_token, res.data.refresh_token, toCamel(res.data.user));
      router.push('/dashboard');
    } catch (e: any) {
      setError(e?.offline ? 'No connection. Please try again when you have signal.' : (e?.detail || 'Invalid code.'));
    }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow p-8">
        <div className="text-center mb-6"><span className="text-4xl">🌿</span>
          <h1 className="text-2xl font-bold text-brand-green mt-2">Join KohwAI</h1>
          <p className="text-sm text-gray-500">Free for Zimbabwean farmers</p>
        </div>
        {error && <p className="text-red-600 text-sm mb-4 bg-red-50 rounded-lg p-2">{error}</p>}
        {step === 'form' ? (
          <div className="space-y-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input type="tel" placeholder="+263 7X XXX XXXX" value={form.phone}
                onChange={e => setForm({...form, phone:e.target.value})}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-brand-green focus:outline-none" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">District</label>
              <select value={form.district} onChange={e => setForm({...form, district:e.target.value})}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-brand-green focus:outline-none">
                <option value="">Select…</option>
                {DISTRICTS.map(d => <option key={d}>{d}</option>)}
              </select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
              <select value={form.language} onChange={e => setForm({...form, language:e.target.value})}
                className="w-full border border-gray-300 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-brand-green focus:outline-none">
                <option value="en">English</option><option value="sn">Shona</option><option value="nd">Ndebele</option>
              </select></div>
            <ConsentSummary />
            <label className="flex items-start gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} className="mt-1" />
              I accept the Terms and Privacy Policy and want SMS alerts for my district
            </label>
            <button onClick={requestOtp} disabled={loading||!form.phone||!form.district||!accepted}
              className="w-full mt-2 bg-brand-green text-white rounded-xl py-3 font-semibold disabled:opacity-50">
              {loading ? 'Sending…' : 'Send Verification Code'}
            </button>
            <p className="text-center text-sm text-gray-500">Already registered? <Link href="/login" className="text-brand-green font-medium">Log in</Link></p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-4">Code sent to <strong>{form.phone}</strong></p>
            <input type="text" placeholder="6-digit code" maxLength={6} value={otp}
              onChange={e => setOtp(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-3 py-2.5 mb-4 text-center text-2xl tracking-widest focus:ring-2 focus:ring-brand-green focus:outline-none" />
            <button onClick={verify} disabled={loading||otp.length<6}
              className="w-full bg-brand-green text-white rounded-xl py-3 font-semibold disabled:opacity-50">
              {loading ? 'Verifying…' : 'Complete Registration'}
            </button>
            <button onClick={() => setStep('form')} className="w-full text-sm text-gray-500 mt-3">← Change details</button>
          </>
        )}
      </div>
    </div>
  );
}
