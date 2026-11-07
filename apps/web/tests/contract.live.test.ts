/**
 * LIVE contract test: runs the real lib/offline.ts against a running backend.
 * Skipped unless KOHWAI_API_URL is set (CI job / local: KOHWAI_API_URL=http://127.0.0.1:8000 ADMIN_PHONE=0779990055 npm test).
 * Needs the API in development mode with EXPOSE_DEV_OTP=true and an admin created with backend/scripts/seed_admin.py.
 */
import { describe, it, expect, beforeAll } from 'vitest';

const API = process.env.KOHWAI_API_URL;
const ADMIN = process.env.ADMIN_PHONE;
process.env.NEXT_PUBLIC_API_URL = API || 'http://127.0.0.1:8000';

describe.skipIf(!API || !ADMIN)('web <-> backend contract (live)', () => {
  let apiClient: any, offline: any, db: any;
  const rnd = () => `07${Math.floor(10000000 + Math.random() * 89999999)}`;

  async function login(phone: string, district = 'Chipinge') {
    const { default: axios } = await import('axios');
    const base = `${API}/api/v1`;
    const j = (await axios.post(`${base}/auth/otp/request`, { phone })).data;
    const t = (await axios.post(`${base}/auth/otp/verify`, { phone, otp: j.dev_otp, district, accept_terms: true })).data;
    return t.access_token as string;
  }
  const as = (token: string) => { apiClient.defaults.headers.common.Authorization = `Bearer ${token}`; };

  beforeAll(async () => {
    ({ apiClient } = await import('@/lib/api'));
    offline = await import('@/lib/offline');
    ({ db } = await import('@/lib/db'));
  });

  it('boreholes, reports, listings and an outage — end to end', async () => {
    const admin = await login(ADMIN!);
    const farmer = await login(rnd());
    const buyer = await login(rnd());

    // admin registers a borehole (a verified one)
    as(admin);
    const name = 'Contract BH ' + Date.now();
    await apiClient.post('/mvura/boreholes', { name, village: 'Mutema', district: 'Chipinge', lat: -20.19, lng: 32.62 });

    // farmer: real response, camelCase, verified
    as(farmer);
    let r = await offline.getBoreholes('Chipinge');
    expect(r.source).toBe('network');
    const bh = r.data.find((b: any) => b.name === name);
    expect(bh).toMatchObject({ status: 'working', verified: true, pendingReport: null, pendingReports: 0 });
    expect(typeof bh.lastVerified).toBe('string');

    // report: reaches the server as PENDING and does NOT change the public status
    expect((await offline.reportBorehole({ id: bh.id, status: 'dry' })).status).toBe('sent');
    r = await offline.getBoreholes('Chipinge');
    expect(r.data.find((b: any) => b.id === bh.id)).toMatchObject({ status: 'working', pendingReport: 'dry', pendingReports: 1 });

    // outage: write is queued, read falls back to the saved REAL copy
    const live = apiClient.defaults.baseURL;
    apiClient.defaults.baseURL = 'http://127.0.0.1:1';
    expect((await offline.reportBorehole({ id: bh.id, status: 'broken' })).status).toBe('queued');
    const cached = await offline.getBoreholes('Chipinge');
    expect(cached.source).toBe('cache');
    expect(cached.data.some((b: any) => b.id === bh.id)).toBe(true);
    expect(await offline.outboxCounts()).toEqual({ pending: 1, failed: 0 });

    // back online: replay -> the farmer's single pending report is UPDATED to 'broken', not duplicated
    apiClient.defaults.baseURL = live;
    expect(await offline.flushOutbox()).toMatchObject({ sent: 1, failed: 0, stillOffline: false });
    r = await offline.getBoreholes('Chipinge');
    expect(r.data.find((b: any) => b.id === bh.id)).toMatchObject({ status: 'working', pendingReport: 'broken', pendingReports: 1 });

    // listings: camelCase payload accepted, price comes back as a number, phone stays private by default
    const title = 'SC403 ' + Date.now();
    const posted = await offline.addListing({ type: 'seed', title, quantity: 40, unit: 'kg', priceUsd: 1.8, district: 'Chipinge' });
    expect(posted.status).toBe('sent');
    as(buyer);
    const listings = await offline.getListings('seed');
    const mine = listings.data.find((l: any) => l.title === title);
    expect(mine).toMatchObject({ priceUsd: 1.8, sellerPhone: null, isMine: false });

    // server-side validation reaches the UI (negative price) and nothing is queued
    as(farmer);
    await expect(offline.addListing({ type: 'seed', title: 'bad', quantity: 1, unit: 'kg', priceUsd: -1, district: 'Chipinge' }))
      .rejects.toMatchObject({ status: 422, offline: false });
    expect(await offline.outboxCounts()).toEqual({ pending: 0, failed: 0 });
  });

  it('consent, PIN, export and deletion through the real web client', async () => {
    const { default: axios } = await import('axios');
    const base = `${API}/api/v1`;
    const ph = rnd();
    const j = (await axios.post(`${base}/auth/otp/request`, { phone: ph })).data;

    // new number without ticking the box -> clear 400, and the SAME code still works afterwards
    apiClient.defaults.headers.common.Authorization = '';
    await expect(apiClient.post('/auth/otp/verify', { phone: ph, otp: j.dev_otp, district: 'Chipinge' }))
      .rejects.toMatchObject({ status: 400, offline: false, detail: expect.stringMatching(/accept the Terms/i) });
    const v = (await apiClient.post('/auth/otp/verify', { phone: ph, otp: j.dev_otp, district: 'Chipinge', accept_terms: true })).data;
    expect(v.user).toMatchObject({ needs_consent: false, sms_alerts: true, has_pin: false });
    as(v.access_token);

    // validated preferences
    await expect(apiClient.patch('/auth/me', { district: 'Atlantis' })).rejects.toMatchObject({ status: 422 });
    expect((await apiClient.patch('/auth/me', { sms_alerts: false })).data.sms_alerts).toBe(false);

    // PIN: weak rejected, good accepted
    await expect(apiClient.put('/auth/me/pin', { pin: '1234' })).rejects.toMatchObject({ status: 422 });
    await apiClient.put('/auth/me/pin', { pin: '4829' });
    expect((await apiClient.get('/auth/me')).data.has_pin).toBe(true);

    // export has my data and never the PIN hash
    const exp = (await apiClient.get('/auth/me/export')).data;
    expect(exp.profile.phone).toContain(ph.slice(1));
    expect(JSON.stringify(exp)).not.toMatch(/pin_hash|\$2b\$/);

    // delete -> token no longer works
    await apiClient.post('/auth/me/delete-account', { confirm: true });
    await expect(apiClient.get('/auth/me')).rejects.toMatchObject({ status: 401 });
  });
});
