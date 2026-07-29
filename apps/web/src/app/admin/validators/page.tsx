'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function AdminValidatorsPage() {
  const [validators, setValidators] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/community/validators').then(r => setValidators(r.data)).catch(() => setError('Could not load validators.'));
  }, []);

  return (
    <AppShell title="Validators">
      <h1 className="text-xl font-bold text-gray-900 mb-2">👥 Validators &amp; admins</h1>
      <p className="text-sm text-gray-500 mb-4">
        New validators are promoted via the server-side seed script — role changes aren't exposed over the API for security.
      </p>
      {error && <p className="text-sm text-brand-red">{error}</p>}
      <div className="flex flex-col gap-2">
        {validators.map(v => (
          <div key={v.id} className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center">
            <div>
              <p className="text-sm font-medium text-gray-900">{v.phone}</p>
              <p className="text-xs text-gray-500">{v.district || 'No district set'} · {v.roles.join(', ')}</p>
            </div>
            <span className="text-xs font-semibold text-brand-green">{v.reports_reviewed} reviewed</span>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
