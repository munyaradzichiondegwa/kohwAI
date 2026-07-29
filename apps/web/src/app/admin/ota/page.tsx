'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function AdminOtaPage() {
  const [version, setVersion] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiClient.get('/settings').then(r => {
      const s = r.data.find((x: any) => x.key === 'min_app_version');
      if (s) setVersion(s.value.web || '');
    }).catch(() => setError('Could not load version config.'));
  }, []);

  async function save() {
    try {
      await apiClient.put('/settings/min_app_version', { value: { web: version } });
      setSaved(true); setTimeout(() => setSaved(false), 1500);
    } catch { setError('Save failed — admin access required.'); }
  }

  return (
    <AppShell title="OTA / Versions">
      <h1 className="text-xl font-bold text-gray-900 mb-2">📦 App version gate</h1>
      <p className="text-sm text-gray-500 mb-4">
        The PWA checks this on load; below this version, users are prompted to refresh.
        There is no compiled native binary to push OTA updates to yet — this controls the web app only.
      </p>
      {error && <p className="text-sm text-brand-red mb-3">{error}</p>}
      <div className="bg-white rounded-xl border border-gray-100 p-4">
        <label className="text-sm text-gray-700">
          Minimum web version
          <input value={version} onChange={e => setVersion(e.target.value)} placeholder="1.0.0"
            className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </label>
        <button onClick={save} className="mt-3 w-full bg-brand-green text-white rounded-xl py-2.5 text-sm font-medium">
          {saved ? 'Saved ✓' : 'Save'}
        </button>
      </div>
    </AppShell>
  );
}
