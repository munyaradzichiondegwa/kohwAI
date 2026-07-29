'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/analytics/overview').then(r => setData(r.data)).catch(() => setError('Could not load analytics.'));
  }, []);

  return (
    <AppShell title="Analytics">
      <h1 className="text-xl font-bold text-gray-900 mb-4">📊 Platform analytics</h1>
      {error && <p className="text-sm text-brand-red">{error}</p>}
      {data && (
        <pre className="bg-white border border-gray-100 rounded-xl p-4 text-xs overflow-x-auto text-gray-700">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
      <p className="text-xs text-gray-400 mt-4">
        Raw counts direct from the database. A future iteration can add trend charts once there's
        enough historical data to make a trend line meaningful.
      </p>
    </AppShell>
  );
}
