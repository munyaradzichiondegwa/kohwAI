'use client';
import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

export default function SimbaPage() {
  const user = useAuthStore(s => s.user);
  const [capacity, setCapacity] = useState(2000);
  const [panelWatts, setPanelWatts] = useState(300);
  const [currentPct, setCurrentPct] = useState(70);
  const [loadWatts, setLoadWatts] = useState(50);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Fully offline, client-side estimate (works with zero network — matches the
  // PRD requirement that the load calculator "must work fully offline").
  function offlineEstimate() {
    const points = [];
    let batteryWh = (currentPct / 100) * capacity;
    const dailyGenWh = panelWatts * 5.5 * 0.75; // assumes ~5.5 average sun-hours (Zimbabwe dry-season typical)
    for (let h = 0; h <= 48; h += 6) {
      const isDaylight = (h % 24) >= 6 && (h % 24) <= 18;
      const genWh = isDaylight ? (dailyGenWh / 12) * 6 : 0;
      const useWh = loadWatts * 6;
      if (h > 0) batteryWh = Math.max(0, Math.min(capacity, batteryWh + genWh - useWh));
      points.push({ hours_from_now: h, estimated_battery_pct: Math.round((100 * batteryWh / capacity) * 10) / 10 });
    }
    setForecast({
      district: user?.district || 'your area', battery_capacity_wh: capacity, panel_watts: panelWatts,
      data_source: 'Offline estimate (typical dry-season sun-hours) — reconnect for live satellite data',
      forecast: points,
      disclaimer: 'Simplified energy-balance estimate, not a professional solar sizing calculation.',
    });
  }

  async function runForecast() {
    setLoading(true);
    try {
      const res = await apiClient.get('/simba/battery-forecast', {
        params: {
          district: user?.district || 'Harare', battery_capacity_wh: capacity,
          panel_watts: panelWatts, current_pct: currentPct, load_watts: loadWatts,
        },
      });
      setForecast(res.data);
    } catch {
      offlineEstimate();
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Simba — Energy">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">☀️ Battery &amp; solar forecast</h1>
        <p className="text-sm text-gray-500 mt-1">48-hour estimate. Works fully offline using typical sun-hours.</p>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm text-gray-700">
            Battery capacity (Wh)
            <input type="number" value={capacity} onChange={e => setCapacity(+e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label className="text-sm text-gray-700">
            Panel wattage (W)
            <input type="number" value={panelWatts} onChange={e => setPanelWatts(+e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label className="text-sm text-gray-700">
            Current charge (%)
            <input type="number" min={0} max={100} value={currentPct} onChange={e => setCurrentPct(+e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label className="text-sm text-gray-700">
            Average load (W)
            <input type="number" value={loadWatts} onChange={e => setLoadWatts(+e.target.value)}
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
        </div>
        <button onClick={runForecast} disabled={loading}
          className="mt-4 w-full bg-brand-green text-white rounded-xl py-2.5 text-sm font-medium disabled:opacity-50">
          {loading ? 'Calculating…' : 'Calculate 48h forecast'}
        </button>
      </section>

      {forecast && (
        <section className="bg-white rounded-2xl border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Estimated battery charge</h2>
          <div className="flex flex-col gap-2">
            {forecast.forecast.map((p: any) => (
              <div key={p.hours_from_now} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-16">+{p.hours_from_now}h</span>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${
                    p.estimated_battery_pct > 50 ? 'bg-brand-green' : p.estimated_battery_pct > 20 ? 'bg-brand-amber' : 'bg-brand-red'
                  }`} style={{ width: `${p.estimated_battery_pct}%` }} />
                </div>
                <span className="text-xs font-semibold w-10 text-right">{p.estimated_battery_pct}%</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">Source: {forecast.data_source}</p>
          <p className="text-xs text-gray-400 mt-1">{forecast.disclaimer}</p>
        </section>
      )}
    </AppShell>
  );
}
