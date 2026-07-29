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
  synced: boolean;
}

interface ValidatorReportItem {
  id?: number;
  kind: 'crop' | 'livestock' | 'borehole' | 'market';
  summary: string;
  district: string;
  reporterPhone: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
  reviewedBy?: string;
}

interface KVItem { key: string; value: any; }

class KohwaiDB extends Dexie {
  alerts!: Table<Alert>;
  boreholes!: Table<Borehole>;
  listings!: Table<MarketListing>;
  diagnosisQueue!: Table<OfflineDiagnosisQueueItem>;
  validatorQueue!: Table<ValidatorReportItem>;
  kv!: Table<KVItem>;

  constructor() {
    super('KohwaiDB');
    this.version(2).stores({
      alerts:        '++id, type, severity, district, createdAt',
      boreholes:     '++id, status, district',
      listings:      '++id, type, district, expiresAt',
      diagnosisQueue:'++id, createdAt, synced, kind',
      validatorQueue:'++id, kind, status, district, createdAt',
      kv:            '&key',
    });
  }
}

export const db = new KohwaiDB();
export type { OfflineDiagnosisQueueItem, ValidatorReportItem };
