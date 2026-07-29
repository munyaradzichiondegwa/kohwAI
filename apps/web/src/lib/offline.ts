import { apiClient } from './api';
import { db } from './db';
import type { Alert, Borehole, MarketListing } from '@kohwai/shared/types';

/**
 * These are clearly-labelled seed/demo records, not live data from
 * Agritex, ZINWA, or ZESA. They exist so the app is usable and
 * demonstrable before the real backend + data feeds are connected.
 * They are only written to IndexedDB once, on first run.
 */
const SEED_ALERTS: Alert[] = [
  { id: 'seed-1', type: 'weather', severity: 'amber', title: 'Dry spell forecast',
    body: 'Below-average rainfall expected over the next 10 days. Consider drought-tolerant planting.',
    pillar: 'zunde', district: 'Chipinge', createdAt: new Date().toISOString() },
  { id: 'seed-2', type: 'pest', severity: 'red', title: 'Fall Armyworm reported nearby',
    body: 'Community reports of Fall Armyworm in your district. Inspect maize leaves for chewing damage.',
    pillar: 'zunde', district: 'Gokwe', createdAt: new Date().toISOString() },
];

const SEED_BOREHOLES: Borehole[] = [
  { id: 'seed-bh-1', name: 'Chipinge Ward 3 Borehole', village: 'Mutema', lat: -20.19, lng: 32.62,
    status: 'working', lastVerified: new Date().toISOString() },
  { id: 'seed-bh-2', name: 'Gokwe North Borehole 12', village: 'Nembudziya', lat: -17.99, lng: 28.93,
    status: 'low', lastVerified: new Date().toISOString() },
  { id: 'seed-bh-3', name: 'Binga Kariangwe Borehole', village: 'Kariangwe', lat: -17.62, lng: 27.34,
    status: 'dry', lastVerified: new Date().toISOString() },
];

const SEED_LISTINGS: MarketListing[] = [
  { id: 'seed-ml-1', type: 'seed', title: 'SC403 Maize Seed', description: 'Certified seed, 10kg bags',
    quantity: 40, unit: 'kg', priceUsd: 1.8, district: 'Gweru', sellerPhone: '077•••1234',
    expiresAt: new Date(Date.now() + 14 * 86400000).toISOString() },
  { id: 'seed-ml-2', type: 'produce', title: 'Fresh Tomatoes', description: 'Grade A, harvested this week',
    quantity: 200, unit: 'kg', priceUsd: 0.6, district: 'Mutare', sellerPhone: '071•••5678',
    expiresAt: new Date(Date.now() + 5 * 86400000).toISOString() },
  { id: 'seed-ml-3', type: 'livestock', title: 'Weaner Calves', description: '3 healthy weaners, Brahman cross',
    quantity: 3, unit: 'head', priceUsd: 220, district: 'Kwekwe', sellerPhone: '073•••9012',
    aiVerifiedHealthy: false, expiresAt: new Date(Date.now() + 21 * 86400000).toISOString() },
];

let seeded = false;
async function ensureSeeded() {
  if (seeded) return;
  seeded = true;
  const [aCount, bCount, lCount] = await Promise.all([
    db.alerts.count(), db.boreholes.count(), db.listings.count(),
  ]);
  if (aCount === 0) await db.alerts.bulkAdd(SEED_ALERTS);
  if (bCount === 0) await db.boreholes.bulkAdd(SEED_BOREHOLES);
  if (lCount === 0) await db.listings.bulkAdd(SEED_LISTINGS);
}

/** True once we've confirmed the real backend responded at least once this session. */
export let backendReachable = false;

export async function getAlerts(): Promise<Alert[]> {
  try {
    const res = await apiClient.get('/alerts/active');
    backendReachable = true;
    return res.data;
  } catch {
    await ensureSeeded();
    return db.alerts.toArray();
  }
}

export async function getBoreholes(district?: string): Promise<Borehole[]> {
  try {
    const res = await apiClient.get('/mvura/boreholes' + (district ? `?district=${district}` : ''));
    backendReachable = true;
    return res.data.boreholes || res.data;
  } catch {
    await ensureSeeded();
    const all = await db.boreholes.toArray();
    return district ? all.filter(b => b.village.includes(district)) : all;
  }
}

export async function getListings(type?: MarketListing['type']): Promise<MarketListing[]> {
  try {
    const res = await apiClient.get('/musika/listings' + (type ? `?type=${type}` : ''));
    backendReachable = true;
    return res.data.listings || res.data;
  } catch {
    await ensureSeeded();
    const all = await db.listings.toArray();
    return type ? all.filter(l => l.type === type) : all;
  }
}

export async function addListing(listing: Omit<MarketListing, 'id'>): Promise<MarketListing> {
  try {
    const res = await apiClient.post('/musika/listings', listing);
    backendReachable = true;
    return res.data;
  } catch {
    const withId: MarketListing = { ...listing, id: `local-${Date.now()}` };
    await db.listings.add(withId);
    return withId;
  }
}

export async function reportBorehole(update: Pick<Borehole, 'id' | 'status'> & { note?: string }) {
  try {
    await apiClient.post(`/mvura/boreholes/${update.id}/report`, update);
    backendReachable = true;
  } catch {
    await db.boreholes.where('id').equals(update.id).modify({ status: update.status, lastVerified: new Date().toISOString() });
  }
}
