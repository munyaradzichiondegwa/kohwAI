'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { toCamel } from '@/lib/case';
import { useAuthStore } from '@/stores/authStore';
import ConsentSummary from '@/components/ui/ConsentSummary';

/** Shown to accounts that never accepted the current Terms & Privacy Policy (older accounts, or after a new version). */
export default function ConsentPage() {
  const router = useRouter();
  const { user, accessToken, refreshToken, setAuth } = useAuthStore();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function accept() {
    setBusy(true); setError('');
    try {
      const res = await apiClient.post('/auth/consent', { accept: true });
      if (accessToken && user) setAuth(accessToken, refreshToken || '', { ...user, ...toCamel(res.data) });
      router.replace('/dashboard');
    } catch (e: any) {
      setError(e?.offline ? 'You need a connection to continue. Please try again when you have signal.' : (e?.detail || 'Could not save your choice.'));
    }
    setBusy(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4">
        <h1 className="text-xl font-bold text-gray-900">Before you continue</h1>
        <p className="text-sm text-gray-600">Please review how KohwAI uses your information.</p>
        <ConsentSummary />
        <label className="flex items-start gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)} className="mt-1" />
          I accept the Terms and Privacy Policy
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button onClick={accept} disabled={!accepted || busy}
          className="w-full bg-brand-green text-white rounded-xl py-2.5 font-medium disabled:opacity-50">{busy ? 'Saving…' : 'Continue'}</button>
      </div>
    </div>
  );
}
