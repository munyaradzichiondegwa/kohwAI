import Dexie, { type Table } from 'dexie';
import type { Alert, Borehole, MarketListing } from '@kohwai/shared/types';

interface OfflineDiagnosisQueueItem {
  id?: number;
  imageBase64?: string;
  cropType?: string;
  animalType?: string;
  symptom?: string;
  disease1?: string;
  disease2?: string;
  action?: string;
  kind: 'crop' | 'livestock';
  createdAt: string;
  /** 0 = waiting to sync, 1 = synced. A number, not a boolean: IndexedDB cannot index booleans, so a
   *  `where('synced')` query on `false` silently matched nothing and queued diagnoses never synced. */
  synced: 0 | 1;
}

/** A write made while offline, replayed in order once the network is back. */
interface OutboxItem {
  seq?: number;
  kind: 'borehole_report' | 'listing';
  /** Request path (relative to the API base) and snake_case body, ready to POST as-is. */
  path: string;
  body: Record<string, unknown>;
  createdAt: string;
  status: 'pending' | 'failed';
  attempts: number;
  lastError?: string;
}

interface KVItem { key: string; value: any; }

class KohwaiDB extends Dexie {
  cacheAlerts!: Table<Alert, string>;
  cacheBoreholes!: Table<Borehole, string>;
  cacheListings!: Table<MarketListing, string>;
  outbox!: Table<OutboxItem, number>;
  diagnosisQueue!: Table<OfflineDiagnosisQueueItem, number>;
  kv!: Table<KVItem, string>;

  constructor() {
    super('KohwaiDB');
    // v2 (legacy): tables seeded with invented demo records and keyed by an auto-increment number.
    this.version(2).stores({
      alerts: '++id, type, severity, district, createdAt',
      boreholes: '++id, status, district',
      listings: '++id, type, district, expiresAt',
      diagnosisQueue: '++id, createdAt, synced, kind',
      validatorQueue: '++id, kind, status, district, createdAt',
      kv: '&key',
    });
    // v3: caches keyed by the server's id and holding ONLY real server responses. Legacy tables (which
    // contained fake seed records on every device) are dropped, not migrated.
    this.version(3).stores({
      alerts: null, boreholes: null, listings: null, validatorQueue: null,
      cacheAlerts: 'id, district',
      cacheBoreholes: 'id, district, status',
      cacheListings: 'id, type, district',
      outbox: '++seq, kind, status',
      diagnosisQueue: '++id, createdAt, synced, kind',
      kv: '&key',
    }).upgrade(tx => tx.table('diagnosisQueue').toCollection().modify((i: any) => { i.synced = i.synced ? 1 : 0; }));
  }
}

export const db = new KohwaiDB();
export type { OfflineDiagnosisQueueItem, OutboxItem };
