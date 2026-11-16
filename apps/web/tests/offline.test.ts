/**
 * Behaviour tests for lib/offline.ts using a fake IndexedDB and a scripted network (no server needed).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { apiClient, ApiError } from '@/lib/api';
import { db } from '@/lib/db';
import { getBoreholes, getListings, reportBorehole, addListing, flushOutbox, outboxCounts } from '@/lib/offline';

type Handler = (cfg: any) => { status: number; data: any } | 'offline';
let handler: Handler;
let calls: any[] = [];

beforeEach(async () => {
  calls = [];
  await Promise.all([db.cacheAlerts.clear(), db.cacheBoreholes.clear(), db.cacheListings.clear(), db.outbox.clear(), db.kv.clear()]);
  // Scripted adapter: behaves like the real client (HTTP errors / network errors become ApiError via the interceptor).
  apiClient.defaults.adapter = async (cfg: any) => {
    calls.push({ url: cfg.url, method: cfg.method, data: cfg.data ? JSON.parse(cfg.data) : undefined });
    const r = handler(cfg);
    if (r === 'offline') { const e: any = new Error('Network Error'); e.config = cfg; e.isAxiosError = true; throw e; }
    const res = { status: r.status, statusText: '', data: r.data, headers: {}, config: cfg };
    if (r.status >= 400) { const e: any = new Error('HTTP ' + r.status); e.config = cfg; e.response = res; e.isAxiosError = true; throw e; }
    return res;
  };
});

const BH = [{ id: 'b1', name: 'Mutema', village: 'V', district: 'Chipinge', lat: -20, lng: 32, status: 'working',
              last_verified: '2026-11-01T00:00:00Z', verified: true, pending_report: 'dry', pending_reports: 1 }];

describe('reads', () => {
  it('network success is converted to camelCase and saved for offline use', async () => {
    handler = () => ({ status: 200, data: BH });
    const r = await getBoreholes('Chipinge');
    expect(r.source).toBe('network');
    expect(r.data[0]).toMatchObject({ lastVerified: '2026-11-01T00:00:00Z', pendingReport: 'dry', pendingReports: 1, verified: true });
    expect(await db.cacheBoreholes.count()).toBe(1);
  });

  it('offline: serves the REAL last response, labelled as cache (the old code served invented seed data)', async () => {
    handler = () => ({ status: 200, data: BH });
    await getBoreholes('Chipinge');
    handler = () => 'offline';
    const r = await getBoreholes('Chipinge');
    expect(r.source).toBe('cache');
    expect(r.cachedAt).toBeTruthy();
    expect(r.data.map(b => b.id)).toEqual(['b1']);
    expect(JSON.stringify(r.data)).not.toMatch(/Kariangwe|Gokwe/);          // none of the old fake records
  });

  it('offline with nothing saved: honest empty list, not fake data', async () => {
    handler = () => 'offline';
    const r = await getListings();
    expect(r).toMatchObject({ data: [], source: 'cache' });
  });

  it('server errors are NOT hidden behind cached/fake data', async () => {
    handler = () => ({ status: 500, data: { detail: 'boom' } });
    await expect(getBoreholes()).rejects.toMatchObject({ status: 500, offline: false });
    handler = () => ({ status: 401, data: { detail: 'Not authenticated' } });
    await expect(getListings()).rejects.toBeInstanceOf(ApiError);
  });

  it('a fresh response replaces rows the server has since removed (expired listings disappear)', async () => {
    const L = (id: string) => ({ id, type: 'seed', title: id, quantity: 1, unit: 'kg', price_usd: 2, district: 'Chipinge' });
    handler = () => ({ status: 200, data: [L('a'), L('b')] });
    await getListings();
    handler = () => ({ status: 200, data: [L('b')] });
    await getListings();
    handler = () => 'offline';
    expect((await getListings()).data.map(l => l.id)).toEqual(['b']);
  });
});

describe('writes', () => {
  it('borehole report sends the field the API expects (new_status) — was `status`, rejected with 422 and swallowed', async () => {
    handler = () => ({ status: 200, data: { id: 'r1', status: 'pending' } });
    const out = await reportBorehole({ id: 'b1', status: 'dry', note: 'no water' });
    expect(out.status).toBe('sent');
    expect(calls[0]).toMatchObject({ url: '/mvura/boreholes/b1/report', data: { new_status: 'dry', note: 'no water' } });
  });

  it('listing is sent in snake_case (price_usd, share_phone) — was camelCase, rejected with 422 and swallowed', async () => {
    handler = () => ({ status: 200, data: { id: 'l1', price_usd: 1.8, type: 'seed', title: 'x', quantity: 1, unit: 'kg', district: 'Chipinge' } });
    const out = await addListing({ type: 'seed', title: 'SC403', quantity: 40, unit: 'kg', priceUsd: 1.8, district: 'Chipinge', sharePhone: true });
    expect(out.status).toBe('sent');
    expect(calls[0].data).toMatchObject({ price_usd: 1.8, share_phone: true });
    expect(calls[0].data).not.toHaveProperty('priceUsd');
    if (out.status === 'sent') expect((out.data as any).priceUsd).toBe(1.8);
  });

  it('validation errors surface to the caller instead of being swallowed', async () => {
    handler = () => ({ status: 422, data: { detail: [{ loc: ['body', 'price_usd'], msg: 'must be >= 0' }] } });
    await expect(addListing({ type: 'seed', title: 'x', quantity: 1, unit: 'kg', priceUsd: -1, district: 'Chipinge' }))
      .rejects.toMatchObject({ status: 422, detail: 'price_usd: must be >= 0' });
    expect(await db.outbox.count()).toBe(0);                 // a rejected write is not queued forever
  });

  it('offline writes are queued (not lost) and replayed in order when back online', async () => {
    handler = () => 'offline';
    expect((await reportBorehole({ id: 'b1', status: 'dry' })).status).toBe('queued');
    expect((await addListing({ type: 'seed', title: 'A', quantity: 1, unit: 'kg', priceUsd: 1, district: 'Chipinge' })).status).toBe('queued');
    expect(await outboxCounts()).toEqual({ pending: 2, failed: 0 });

    const r1 = await flushOutbox();                          // still offline: nothing lost, nothing sent
    expect(r1).toMatchObject({ sent: 0, stillOffline: true });
    expect((await outboxCounts()).pending).toBe(2);

    calls = []; handler = () => ({ status: 200, data: {} });
    const r2 = await flushOutbox();
    expect(r2).toMatchObject({ sent: 2, failed: 0, stillOffline: false });
    expect(calls.map(c => c.url)).toEqual(['/mvura/boreholes/b1/report', '/musika/listings']);    // original order
    expect(await outboxCounts()).toEqual({ pending: 0, failed: 0 });
  });

  it('a permanently rejected queued write is parked as failed, not retried forever', async () => {
    handler = () => 'offline';
    await reportBorehole({ id: 'gone', status: 'dry' });
    handler = () => ({ status: 404, data: { detail: 'Borehole not found' } });
    expect(await flushOutbox()).toMatchObject({ sent: 0, failed: 1 });
    expect(await outboxCounts()).toEqual({ pending: 0, failed: 1 });
    expect((await db.outbox.toArray())[0].lastError).toBe('Borehole not found');
    calls = [];
    await flushOutbox();
    expect(calls).toHaveLength(0);                           // not retried
  });

  it('a 5xx while replaying keeps the item pending for the next attempt', async () => {
    handler = () => 'offline';
    await addListing({ type: 'seed', title: 'A', quantity: 1, unit: 'kg', priceUsd: 1, district: 'Chipinge' });
    handler = () => ({ status: 503, data: { detail: 'down' } });
    await flushOutbox();
    expect(await outboxCounts()).toEqual({ pending: 1, failed: 0 });
  });
});

describe('diagnosis queue index', () => {
  it('queued diagnoses are findable by the sync query (booleans cannot be indexed; numbers can)', async () => {
    await db.diagnosisQueue.clear();
    await db.diagnosisQueue.add({ kind: 'crop', cropType: '1', symptom: '1', createdAt: new Date().toISOString(), synced: 0 });
    await db.diagnosisQueue.add({ kind: 'crop', cropType: '1', symptom: '2', createdAt: new Date().toISOString(), synced: 1 });
    expect(await db.diagnosisQueue.where('synced').equals(0).count()).toBe(1);
  });
});
