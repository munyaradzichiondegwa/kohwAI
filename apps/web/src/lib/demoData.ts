/**
 * DEMO DATA — invented records for sales demos / screenshots ONLY.
 * Shown solely when NEXT_PUBLIC_DEMO_MODE=true AND there is neither a server response nor a saved copy of
 * real data. The UI must label anything with source === 'demo'. Never enabled in production builds.
 */
import type { Alert, Borehole, MarketListing } from '@kohwai/shared/types';

export const DEMO_ALERTS: Alert[] = [
  { id: 'demo-1', type: 'weather', severity: 'amber', title: 'DEMO: Dry spell', body: 'Demo record — not real data.',
    pillar: 'zunde', district: 'Chipinge', createdAt: new Date().toISOString() },
];
export const DEMO_BOREHOLES: Borehole[] = [
  { id: 'demo-bh-1', name: 'DEMO Borehole', village: 'Demo Village', lat: -20.19, lng: 32.62, status: 'working',
    lastVerified: new Date().toISOString(), verified: true },
];
export const DEMO_LISTINGS: MarketListing[] = [
  { id: 'demo-ml-1', type: 'seed', title: 'DEMO Maize Seed', description: 'Demo record — not real data.', quantity: 10,
    unit: 'kg', priceUsd: 1.5, district: 'Chipinge' },
];
