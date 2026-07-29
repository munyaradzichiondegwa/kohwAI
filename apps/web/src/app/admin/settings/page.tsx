'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  function load() {
    apiClient.get('/settings').then(r => setSettings(r.data)).catch(() => setError('Could not load settings.'));
  }
  useEffect(load, []);

  async function toggleFlag(flagKey: string) {
    const flagsSetting = settings.find(s => s.key === 'feature_flags');
    if (!flagsSetting) return;
    setSaving(flagKey);
    const newValue = { ...flagsSetting.value, [flagKey]: !flagsSetting.value[flagKey] };
    try {
      await apiClient.put('/settings/feature_flags', { value: newValue });
      load();
    } catch { /* likely not admin, or offline */ }
    setSaving(null);
  }

  const flags = settings.find(s => s.key === 'feature_flags')?.value || {};

  return (
    <AppShell title="Settings">
      <h1 className="text-xl font-bold text-gray-900 mb-4">⚙️ Feature flags</h1>
      {error && <p className="text-sm text-brand-red mb-3">{error}</p>}
      <div className="flex flex-col gap-2">
        {Object.entries(flags).map(([key, value]) => (
          <div key={key} className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-gray-900">{key.replace(/_/g, ' ')}</p>
              {(key === 'musika_insurance_enrollment' || key === 'livestock_ai_photo_diagnosis') && (
                <p className="text-xs text-gray-400 mt-0.5">Requires external integration not yet configured</p>
              )}
            </div>
            <button onClick={() => toggleFlag(key)} disabled={saving === key}
              className={`w-11 h-6 rounded-full transition-colors relative disabled:opacity-50 ${value ? 'bg-brand-green' : 'bg-gray-300'}`}>
              <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
