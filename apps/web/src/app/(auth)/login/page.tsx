'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { toCamel } from '@/lib/case';
import { useAuthStore } from '@/stores/authStore';
import ConsentSummary from '@/components/ui/ConsentSummary';

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore(s => s.setAuth);
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Shown only when the server says this number has no account yet: creating one needs explicit consent.
  const [needsTerms, setNeedsTerms] = useState(false);
  const [accepted, setAccepted] = useState(false);

  async function requestOtp() {
    setLoading(true); setError('');
    try {
      await apiClient.post('/auth/otp/request', { phone });
      setStep('otp');
    } catch (e: any) {
      // Say what actually went wrong (bad number, too many requests, no connection) — never pretend to be "offline".
      setError(e?.offline ? 'You need a connection to sign in. After you have signed in once, KohwAI works offline.' : (e?.detail || 'Could not send the code.'));
    } finally { setLoading(false); }
  }

  async function verifyOtp() {
    setLoading(true); setError('');
    try {
      const res = await apiClient.post('/auth/otp/verify', { phone, otp, accept_terms: accepted });
      setAuth(res.data.access_token, res.data.refresh_token, toCamel(res.data.user));
      router.push(res.data.user.needs_consent ? '/consent' : '/dashboard');
    } catch (e: any) {
      if (e?.status === 400 && /accept the Terms/i.test(e?.detail || '')) {
        setNeedsTerms(true);        // new number: the same code still works once the box is ticked
        setError('');
      } else {
        setError(e?.offline ? 'No connection. Please try again when you have signal.' : (e?.detail || 'Invalid code.'));
      }
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow p-8">
        <div className="text-center mb-6">
          <span className="text-4xl">🌿</span>
          <h1 className="text-2xl font-bold text-brand-green mt-2">KohwAI</h1>
          <p className="text-sm text-gray-500">Climate Resilience Super-App</p>
        </div>
        {error && <p className="text-red-600 text-sm mb-4 bg-red-50 rounded-lg p-2">{error}</p>}
        {step === 'phone' ? (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <input type="tel" placeholder="+263 7X XXX XXXX" value={phone} onChange={e => setPhone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-green" />
            <button onClick={requestOtp} disabled={loading || !phone}
              className="w-full bg-brand-green text-white rounded-lg py-2 font-medium disabled:opacity-50">
              {loading ? 'Sending...' : 'Send code'}
            </button>
            <p className="text-center text-sm text-gray-500 mt-4">New here? <Link href="/register" className="text-brand-green font-medium">Create an account</Link></p>
          </>
        ) : (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Enter the 6-digit code</label>
            <input type="text" inputMode="numeric" placeholder="6-digit code" maxLength={6} value={otp} onChange={e => setOtp(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-green" />
            {needsTerms && (
              <div className="mb-4 space-y-2">
                <p className="text-sm text-gray-700">This number has no account yet. To create one, please accept the Terms and Privacy Policy.</p>
                <ConsentSummary />
                <label className="flex items-start gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} className="mt-1" />
                  I accept the Terms and Privacy Policy
                </label>
              </div>
            )}
            <button onClick={verifyOtp} disabled={loading || otp.length < 6 || (needsTerms && !accepted)}
              className="w-full bg-brand-green text-white rounded-lg py-2 font-medium disabled:opacity-50">
              {loading ? 'Verifying...' : needsTerms ? 'Create account' : 'Verify & Log In'}
            </button>
            <button onClick={() => { setStep('phone'); setNeedsTerms(false); setAccepted(false); }} className="w-full text-sm text-gray-500 mt-2">← Change number</button>
          </>
        )}
      </div>
    </div>
  );
}
