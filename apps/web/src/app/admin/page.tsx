'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export default function AdminPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/analytics/overview')
      .then(r => setData(r.data))
      .catch(() => setError('Could not load overview — admin access required, and a backend connection.'));
  }, []);

  const STAT = ({ label, value }: { label: string; value: any }) => (
    <div className="bg-white rounded-xl border border-gray-100 p-4">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );

  return (
    <AppShell title="Admin">
      <section className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">Admin overview</h1>
        <p className="text-sm text-gray-500 mt-1">Live counts from the database — nothing here is estimated.</p>
      </section>

      {error && <p className="text-sm text-brand-red mb-4">{error}</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 mb-6">
            <STAT label="Total users" value={data.total_users} />
            <STAT label="New users (7d)" value={data.new_users_last_7_days} />
            <STAT label="Diagnoses (7d)" value={data.diagnoses_last_7_days} />
            <STAT label="Active alerts" value={data.active_alerts} />
            <STAT label="Market listings" value={data.active_market_listings} />
            <STAT label="Pending validation" value={data.pending_validation_queue} />
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
            <p className="text-sm font-semibold text-gray-800 mb-2">Boreholes by status</p>
            {Object.entries(data.boreholes_by_status || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm py-1">
                <span className="capitalize text-gray-600">{k}</span><span className="font-medium">{v as any}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mb-6">Generated at {new Date(data.generated_at).toLocaleString()}</p>
        </>
      )}

      <div className="grid grid-cols-3 gap-2">
        <Link href="/admin/validators" className="bg-white border border-gray-100 rounded-xl p-3 text-center text-sm font-medium">👥 Validators</Link>
        <Link href="/admin/settings" className="bg-white border border-gray-100 rounded-xl p-3 text-center text-sm font-medium">⚙️ Settings</Link>
        <Link href="/admin/ota" className="bg-white border border-gray-100 rounded-xl p-3 text-center text-sm font-medium">📦 OTA / Versions</Link>
      </div>
    </AppShell>
  );
}
