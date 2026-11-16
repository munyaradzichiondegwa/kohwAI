// Shared types used across web & mobile

export type Language = 'en' | 'sn' | 'nd';

export type PillarKey = 'zunde' | 'mvura' | 'simba' | 'musika' | 'livestock';

export type StatusColor = 'green' | 'amber' | 'red' | 'darkRed' | 'blue';

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface DiagnosisResult {
  rank: number;
  disease: string;
  confidence: number;            // 0–1
  treatmentAdvice: string;
  isRespiratory: boolean;
}

export interface LivestockDiagnosisResult {
  visionResults: DiagnosisResult[];
  audioResults?: DiagnosisResult[];
  audioTriggered: boolean;
  overallConfidence: number;
  disclaimer: string;
}

export interface Alert {
  id: string;
  type: 'weather' | 'pest' | 'livestock' | 'water' | 'energy';
  severity: StatusColor;
  title: string;
  body: string;
  pillar: PillarKey;
  district: string;
  createdAt: string;
}

export interface Borehole {
  id: string;
  name: string;
  village: string;
  district?: string;
  lat: number;
  lng: number;
  /** Last status CONFIRMED by a validator/admin. */
  status: 'working' | 'low' | 'dry' | 'broken';
  lastVerified?: string | null;
  /** True once a validator/admin has ever confirmed this borehole. */
  verified?: boolean;
  /** Newest community report still awaiting validation — show it as UNVERIFIED. */
  pendingReport?: 'working' | 'low' | 'dry' | 'broken' | null;
  pendingReports?: number;
  verifiedBy?: string;
}

export interface MarketListing {
  id: string;
  type: 'seed' | 'produce' | 'livestock' | 'input';
  title: string;
  description?: string | null;
  quantity: number;
  unit: string;
  priceUsd: number;
  district: string;
  /** Present only when the seller opted in to sharing their number. */
  sellerPhone?: string | null;
  isMine?: boolean;
  aiVerifiedHealthy?: boolean;
  expiresAt?: string | null;
}

export interface UserProfile {
  id: string;
  phone: string;
  language: Language;
  district: string;
  roles: ('farmer' | 'validator' | 'admin' | 'ngo')[];
  createdAt: string;
  /** true until the current Terms & Privacy Policy version has been accepted */
  needsConsent?: boolean;
  smsAlerts?: boolean;
  hasPin?: boolean;
}
