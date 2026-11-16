import { describe, it, expect } from 'vitest';
import { toCamel, toSnake } from '@/lib/case';
import { simulateBattery, daylightOverlapHours, zimbabweHourNow } from '@/lib/battery';
import { currentSeason } from '@/lib/season';
import { diagnoseCrop, diagnoseLivestock, CROP_SYMPTOMS, LIVESTOCK_SYMPTOMS } from '@/lib/rulesEngine';
import { messageFromBody } from '@/lib/api';
import rules from '@kohwai/shared/rules/rules.json';

describe('case conversion', () => {
  it('round-trips the field names that used to break (priceUsd/price_usd, lastVerified/last_verified)', () => {
    expect(toSnake({ priceUsd: 1.8, sellerPhone: 'x', sharePhone: true, expiresAt: 'd' }))
      .toEqual({ price_usd: 1.8, seller_phone: 'x', share_phone: true, expires_at: 'd' });
    expect(toCamel([{ last_verified: 'd', pending_reports: 1, nested: { is_mine: true } }]))
      .toEqual([{ lastVerified: 'd', pendingReports: 1, nested: { isMine: true } }]);
  });
});

describe('battery model (must match backend simulate_battery)', () => {
  it('conserves energy: 1000W*5kWh*0.75 = 3750Wh -> +37.5% of 10kWh after 24h (old code: 56.2%)', () => {
    const f = simulateBattery(10000, 1000, 0, 0, 5.0, 0);
    expect(f[4]).toEqual({ hours_from_now: 24, estimated_battery_pct: 37.5 });
  });
  it('respects the clock and never goes negative', () => {
    expect(simulateBattery(10000, 1000, 0, 0, 5, 0)[1].estimated_battery_pct).toBe(0);
    expect(simulateBattery(10000, 1000, 0, 0, 5, 12)[1].estimated_battery_pct).toBeGreaterThan(0);
    expect(Math.min(...simulateBattery(1000, 100, 100, 100, 5, 19).map(p => p.estimated_battery_pct))).toBeGreaterThanOrEqual(0);
  });
  it('daylight overlap + Zimbabwe local hour', () => {
    expect(daylightOverlapHours(0, 24)).toBe(12);
    expect(daylightOverlapHours(5, 7)).toBe(1);
    expect(zimbabweHourNow(new Date('2026-11-06T10:30:00Z'))).toBe(12.5);   // UTC+2
  });
});

describe('insurance season label', () => {
  it('runs Nov..Oct', () => {
    expect(currentSeason(new Date(2026, 10, 5))).toBe('2026-27');
    expect(currentSeason(new Date(2027, 2, 31))).toBe('2026-27');
    expect(currentSeason(new Date(2027, 9, 31))).toBe('2026-27');
    expect(currentSeason(new Date(2027, 10, 1))).toBe('2027-28');
  });
});

describe('client rules come from the shared JSON (single source of truth)', () => {
  it('has no invented phone numbers and honest unknowns', () => {
    expect(JSON.stringify(rules)).not.toContain('0800');
    const fmd = diagnoseLivestock('3', '1');
    expect(fmd.disease).toBe('Foot and Mouth Disease');
    expect(fmd.notifiable).toBe(true);
    expect(fmd.action).toContain('your nearest Veterinary office');
    const unknown = diagnoseCrop('3', '2');
    expect(unknown.known).toBe(false);
    expect(unknown.disease2).toBeNull();
  });
  it('every advertised symptom has a stable code', () => {
    expect(CROP_SYMPTOMS.map(s => s.code)).toEqual(['1', '2', '3', '4', '5']);
    expect(LIVESTOCK_SYMPTOMS.find(s => s.code === '3')!.label).toMatch(/Blisters/);
  });
});

describe('FastAPI error messages', () => {
  it('flattens validation errors and plain details', () => {
    expect(messageFromBody({ detail: 'Nope' }, 'x')).toBe('Nope');
    expect(messageFromBody({ detail: [{ loc: ['body', 'quantity'], msg: 'must be > 0' }] }, 'x')).toBe('quantity: must be > 0');
    expect(messageFromBody({}, 'fallback')).toBe('fallback');
  });
});
