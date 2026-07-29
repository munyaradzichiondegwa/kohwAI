'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore(s => s.setAuth);
  const [phone, setPhone] = useState('');
  const [otp, setOtp]     = useState('');
  const [step, setStep]   = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  const [offlineNotice, setOfflineNotice] = useState(false);

  async function requestOtp() {
    setLoading(true); setError('');
    try {
      await apiClient.post('/auth/otp/request', { phone });
      setStep('otp');
    } catch (e: any) {
      // No backend reachable — fall back to local offline mode rather than
      // dead-ending the user. This is clearly surfaced in the UI, not hidden.
      setOfflineNotice(true);
      setStep('otp');
    } finally { setLoading(false); }
  }

  async function verifyOtp() {
    setLoading(true); setError('');
    try {
      const res = await apiClient.post('/auth/otp/verify', { phone, otp });
      setAuth(res.data.access_token, res.data.refresh_token, res.data.user);
      router.push('/dashboard');
    } catch (e: any) {
      if (offlineNotice || !navigator.onLine) {
        // Create a local-only session so the app is usable without a backend.
        setAuth(`local-${Date.now()}`, '', {
          id: `local-${phone}`, phone, language: 'en', district: 'Chipinge',
          roles: ['farmer'], createdAt: new Date().toISOString(),
        });
        router.push('/dashboard');
      } else {
        setError(e?.message || 'Invalid OTP');
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
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        {offlineNotice && step === 'otp' && (
          <p className="text-xs bg-amber-50 text-amber-800 border border-amber-200 rounded-lg p-2 mb-4">
            No backend connection found. Continuing in offline mode — enter any 6 digits to proceed with a local session.
          </p>
        )}
        {step === 'phone' ? (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <input
              type="tel" placeholder="+263 7X XXX XXXX"
              value={phone} onChange={e => setPhone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-green"
            />
            <button
              onClick={requestOtp} disabled={loading || !phone}
              className="w-full bg-brand-green text-white rounded-lg py-2 font-medium disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
          </>
        ) : (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Enter OTP</label>
            <input
              type="text" placeholder="6-digit code" maxLength={6}
              value={otp} onChange={e => setOtp(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-green"
            />
            <button
              onClick={verifyOtp} disabled={loading || otp.length < 6}
              className="w-full bg-brand-green text-white rounded-lg py-2 font-medium disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify & Log In'}
            </button>
            <button onClick={() => setStep('phone')} className="w-full text-sm text-gray-500 mt-2">
              ← Change number
            </button>
          </>
        )}
      </div>
    </div>
  );
}
