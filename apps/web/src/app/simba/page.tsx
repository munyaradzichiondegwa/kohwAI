'use client';
import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient, isOfflineError } from '@/lib/api';
import { simulateBattery, zimbabweHourNow, TYPICAL_IRRADIANCE_KWH_M2 } from '@/lib/battery';
import { useAuthStore } from '@/stores/authStore';

export default function SimbaPage() {
  const user = useAuthStore(s => s.user);
  const [capacity, setCapacity] = useState(2000);
  const [panelWatts, setPanelWatts] = useState(300);
  const [currentPct, setCurrentPct] = useState(70);
  const [loadWatts, setLoadWatts] = useState(50);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  // Fully offline, client-side estimate (the PRD requires the load calculator to work with zero network).
  // Uses the same energy model as the server (lib/battery.ts mirrors backend simba/service.py).
  function offlineEstimate(reason: string) {
    setForecast({
      district: user?.district || 'your area', battery_capacity_wh: capacity, panel_watts: panelWatts,
      data_source: `Offline estimate using typical sunshine (${TYPICAL_IRRADIANCE_KWH_M2} kWh/m²/day) — ${reason}`,
      forecast: simulateBattery(capacity, panelWatts, currentPct, loadWatts, TYPICAL_IRRADIANCE_KWH_M2, zimbabweHourNow()),
      disclaimer: 'Simplified energy-balance estimate, not a professional solar sizing calculation.',
    });
  }

  async function runForecast() {
    setLoading(true); setError(null);
    if (!user?.district) { offlineEstimate('set your district in your profile for live satellite data'); setLoading(false); return; }
    try {
      const res = await apiClient.get('/simba/battery-forecast', {
        params: { district: user.district, battery_capacity_wh: capacity, panel_watts: panelWatts, current_pct: currentPct, load_watts: loadWatts },
      });
      setForecast(res.data);
    } catch (e: any) {
      if (isOfflineError(e)) offlineEstimate('reconnect for live satellite data');
      else setError(e?.detail || 'Could not calculate the forecast.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Simba — Energy">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">☀️ Battery &amp; solar forecast</h1>
        <p className="text-sm text-gray-500 mt-1">48-hour estimate. Works offline using typical sunshine; online it uses live satellite data.</p>
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

      {error && <p className="text-sm text-brand-red mb-3">{error}</p>}
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
