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
  lat: number;
  lng: number;
  status: 'working' | 'low' | 'dry';
  lastVerified: string;
  verifiedBy?: string;
}

export interface MarketListing {
  id: string;
  type: 'seed' | 'produce' | 'livestock' | 'aid';
  title: string;
  description: string;
  quantity: number;
  unit: string;
  priceUsd: number;
  district: string;
  sellerPhone: string;   // masked in UI
  aiVerifiedHealthy?: boolean;
  expiresAt: string;
}

export interface UserProfile {
  id: string;
  phone: string;
  language: Language;
  district: string;
  roles: ('farmer' | 'validator' | 'admin' | 'ngo')[];
  createdAt: string;
}
