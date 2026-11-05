/**
 * Data access with real offline support.
 *
 * Reads : network first -> every successful response is saved to IndexedDB -> if (and only if) there is no
 *         network, serve the last saved real response. HTTP errors (401/403/500...) are NOT hidden behind
 *         cached data: they are thrown so the UI can say what went wrong.
 * Writes: if there is no network the write goes to an outbox and is replayed (in order) when we are back
 *         online. The caller is told 'queued' — never "saved" — so the UI cannot claim something that has not
 *         reached the server.
 * Demo  : invented records are only used when NEXT_PUBLIC_DEMO_MODE=true and nothing real is available.
 */
import type { Table } from 'dexie';
import type { Alert, Borehole, MarketListing } from '@kohwai/shared/types';
import { apiClient, ApiError, isOfflineError } from './api';
import { toCamel, toSnake } from './case';
import { db } from './db';
import { DEMO_ALERTS, DEMO_BOREHOLES, DEMO_LISTINGS } from './demoData';

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === 'true';

export type Source = 'network' | 'cache' | 'demo';
export interface Result<T> { data: T[]; source: Source; /** ISO time of the saved copy when source === 'cache' */ cachedAt?: string; }

async function readThrough<T extends { id: string }>(opts: {
  table: Table<T, string>;
  kvKey: string;
  fetch: () => Promise<T[]>;
  /** remove the cached rows this response replaces (so deleted/expired server rows disappear) */
  clearScope: () => Promise<unknown>;
  readCache: () => Promise<T[]>;
  demo: T[];
}): Promise<Result<T>> {
  try {
    const rows = await opts.fetch();
    await db.transaction('rw', opts.table, db.kv, async () => {
      await opts.clearScope();
      await opts.table.bulkPut(rows);
      await db.kv.put({ key: opts.kvKey, value: new Date().toISOString() });
    });
    return { data: rows, source: 'network' };
  } catch (e) {
    if (!isOfflineError(e)) throw e;                 // server answered with an error: do not mask it
    const cached = await opts.readCache();
    const kv = await db.kv.get(opts.kvKey);
    if (cached.length || kv) return { data: cached, source: 'cache', cachedAt: kv?.value };
    if (DEMO_MODE) return { data: opts.demo, source: 'demo' };
    return { data: [], source: 'cache' };            // offline and nothing saved yet — honest empty state
  }
}

export function getAlerts(): Promise<Result<Alert>> {
  return readThrough<Alert>({
    table: db.cacheAlerts, kvKey: 'cachedAt:alerts', demo: DEMO_ALERTS,
    fetch: async () => toCamel<Alert[]>((await apiClient.get('/alerts/active')).data),
    clearScope: () => db.cacheAlerts.clear(),
    readCache: () => db.cacheAlerts.toArray(),
  });
}

export function getBoreholes(district?: string): Promise<Result<Borehole>> {
  return readThrough<Borehole>({
    table: db.cacheBoreholes, kvKey: `cachedAt:boreholes:${district ?? 'all'}`, demo: DEMO_BOREHOLES,
    fetch: async () => toCamel<Borehole[]>((await apiClient.get('/mvura/boreholes', { params: district ? { district } : {} })).data),
    clearScope: () => (district ? db.cacheBoreholes.where('district').equals(district).delete() : db.cacheBoreholes.clear()),
    readCache: () => (district ? db.cacheBoreholes.where('district').equals(district).toArray() : db.cacheBoreholes.toArray()),
  });
}

export function getListings(type?: MarketListing['type']): Promise<Result<MarketListing>> {
  return readThrough<MarketListing>({
    table: db.cacheListings, kvKey: `cachedAt:listings:${type ?? 'all'}`, demo: DEMO_LISTINGS,
    fetch: async () => toCamel<MarketListing[]>((await apiClient.get('/musika/listings', { params: type ? { type } : {} })).data),
    clearScope: () => (type ? db.cacheListings.where('type').equals(type).delete() : db.cacheListings.clear()),
    readCache: () => (type ? db.cacheListings.where('type').equals(type).toArray() : db.cacheListings.toArray()),
  });
}

// ───────────────────────── writes ─────────────────────────
export type WriteOutcome<T = unknown> = { status: 'sent'; data: T } | { status: 'queued' };

async function write<T>(kind: 'borehole_report' | 'listing', path: string, body: Record<string, unknown>): Promise<WriteOutcome<T>> {
  try {
    const res = await apiClient.post(path, body);
    return { status: 'sent', data: toCamel<T>(res.data) };
  } catch (e) {
    if (!isOfflineError(e)) throw e;                 // validation / auth / server errors go to the UI
    await db.outbox.add({ kind, path, body, createdAt: new Date().toISOString(), status: 'pending', attempts: 0 });
    return { status: 'queued' };
  }
}

export interface NewListing {
  type: MarketListing['type']; title: string; description?: string; quantity: number; unit: string;
  priceUsd: number; district: string; /** seller agrees to show their phone number to other users */ sharePhone?: boolean;
  expiresAt?: string;
}

export function addListing(listing: NewListing) {
  return write<MarketListing>('listing', '/musika/listings', toSnake(listing));
}

export function reportBorehole(update: { id: string; status: 'working' | 'low' | 'dry' | 'broken'; note?: string }) {
  // The API field is `new_status`. The report is stored as PENDING: validators confirm it before it changes
  // what everyone sees.
  return write('borehole_report', `/mvura/boreholes/${update.id}/report`, { new_status: update.status, note: update.note ?? null });
}

export async function outboxCounts(): Promise<{ pending: number; failed: number }> {
  const [pending, failed] = await Promise.all([
    db.outbox.where('status').equals('pending').count(), db.outbox.where('status').equals('failed').count()]);
  return { pending, failed };
}

/** Replay queued writes oldest-first. Stops at the first network failure (still offline). */
export async function flushOutbox(): Promise<{ sent: number; failed: number; stillOffline: boolean }> {
  let sent = 0, failed = 0;
  const items = await db.outbox.where('status').equals('pending').sortBy('seq');
  for (const item of items) {
    try {
      await apiClient.post(item.path, item.body);
      await db.outbox.delete(item.seq!);
      sent++;
    } catch (e) {
      if (isOfflineError(e)) return { sent, failed, stillOffline: true };
      const status = e instanceof ApiError ? e.status : undefined;
      const message = e instanceof ApiError ? e.detail : 'Unknown error';
      // 4xx (except auth/timeouts/rate limits) can never succeed on retry -> park it as failed, don't loop forever
      const permanent = status !== undefined && status >= 400 && status < 500 && ![401, 408, 429].includes(status);
      await db.outbox.update(item.seq!, { status: permanent ? 'failed' : 'pending', attempts: item.attempts + 1, lastError: message });
      if (permanent) failed++; else return { sent, failed, stillOffline: false };
    }
  }
  return { sent, failed, stillOffline: false };
}
