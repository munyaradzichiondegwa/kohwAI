'use client';
import useSWR, { mutate } from 'swr';
import { apiClient } from '@/lib/api';

const SEVERITY_STYLE: Record<string, string> = {
  info:  'bg-brand-blue/10 border-brand-blue/30 text-brand-blue',
  amber: 'bg-brand-amber/10 border-brand-amber/30 text-brand-amber',
  red:   'bg-brand-red/10 border-brand-red/30 text-brand-red',
};

export default function InsightsPanel() {
  const { data: insights = [] } = useSWR('cross-pillar-insights', async () => {
    try { return (await apiClient.get('/intelligence/insights')).data; }
    catch { return []; }
  }, { refreshInterval: 120_000 });

  async function dismiss(id: string) {
    try { await apiClient.post(`/intelligence/insights/${id}/dismiss`); } catch { /* offline: ignore, will resurface next sync */ }
    mutate('cross-pillar-insights', insights.filter((i: any) => i.id !== id), false);
  }

  if (!insights.length) return null;

  return (
    <section className="mt-4 flex flex-col gap-2">
      {insights.map((i: any) => (
        <div key={i.id} className={`border rounded-xl p-3 text-sm ${SEVERITY_STYLE[i.severity] || SEVERITY_STYLE.info}`}>
          <div className="flex justify-between items-start gap-2">
            <p className="flex-1">{i.message}</p>
            <button onClick={() => dismiss(i.id)} className="text-xs opacity-60 hover:opacity-100">✕</button>
          </div>
        </div>
      ))}
    </section>
  );
}
