export const STATUS_COLORS = {
  green:   '#1A7A4A',
  amber:   '#E8A020',
  red:     '#C0392B',
  darkRed: '#7B241C',
  blue:    '#1A5276',
} as const;

export const DISTRICTS = [
  'Chipinge', 'Gokwe', 'Matopos', 'Binga', 'Nyanga',
  'Harare', 'Bulawayo', 'Mutare', 'Gweru', 'Kwekwe',
] as const;

export const AI_CONFIDENCE_GATE       = 0.70;
export const AI_AUDIO_TRIGGER_GATE    = 0.75;
export const OFFLINE_QUEUE_MAX        = 50;
export const ALERT_DEDUP_WINDOW_HOURS = 6;
export const RISK_ALERT_THRESHOLD     = 70;
export const USSD_TIMEOUT_SECONDS     = 120;
export const MAX_USSD_CHARS           = 160;
