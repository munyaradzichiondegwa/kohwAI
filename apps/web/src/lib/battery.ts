/**
 * Offline battery estimate — a TypeScript port of backend/app/modules/simba/service.py (simulate_battery).
 * Daily generation is spread across the 12 daylight hours (06:00–18:00 local), so a full day yields
 * exactly panelWatts * irradiance * 0.75 Wh. The previous copy applied half a day's output to each of
 * three daylight steps (1.5x too much) and assumed it was always midnight.
 */
export const HOURS_STEP = 6;
export const HOURS_HORIZON = 48;
export const DAYLIGHT_START_H = 6;
export const DAYLIGHT_END_H = 18;
export const SYSTEM_LOSS_FACTOR = 0.75;
export const TYPICAL_IRRADIANCE_KWH_M2 = 5.5;

export function daylightOverlapHours(t0: number, t1: number): number {
  let total = 0;
  for (let day = 0; day * 24 < t1; day++) {
    const lo = day * 24 + DAYLIGHT_START_H, hi = day * 24 + DAYLIGHT_END_H;
    total += Math.max(0, Math.min(t1, hi) - Math.max(t0, lo));
  }
  return total;
}

export interface ForecastPoint { hours_from_now: number; estimated_battery_pct: number }

export function simulateBattery(capacityWh: number, panelWatts: number, currentPct: number, loadWatts: number,
                                irradianceKwhM2: number, startHourLocal: number): ForecastPoint[] {
  const dailyGenWh = panelWatts * irradianceKwhM2 * SYSTEM_LOSS_FACTOR;
  let batteryWh = (currentPct / 100) * capacityWh;
  const pct = () => (capacityWh ? Math.round((100 * batteryWh / capacityWh) * 10) / 10 : 0);
  const out: ForecastPoint[] = [{ hours_from_now: 0, estimated_battery_pct: pct() }];
  for (let step = HOURS_STEP; step <= HOURS_HORIZON; step += HOURS_STEP) {
    const gen = dailyGenWh * daylightOverlapHours(startHourLocal + step - HOURS_STEP, startHourLocal + step) / (DAYLIGHT_END_H - DAYLIGHT_START_H);
    batteryWh = Math.max(0, Math.min(capacityWh, batteryWh + gen - loadWatts * HOURS_STEP));
    out.push({ hours_from_now: step, estimated_battery_pct: pct() });
  }
  return out;
}

/** Local hour (Zimbabwe is UTC+2 all year) as a fraction, e.g. 14:30 -> 14.5 */
export function zimbabweHourNow(now: Date = new Date()): number {
  const t = new Date(now.getTime() + 2 * 3600_000);
  return t.getUTCHours() + t.getUTCMinutes() / 60;
}
