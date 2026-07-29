import { en } from './en';
import { sn } from './sn';
import { nd } from './nd';

export type Lang = 'en' | 'sn' | 'nd';
const translations = { en, sn, nd } as const;

export function t(key: keyof typeof en, lang: Lang = 'en'): string {
  return (translations[lang] as any)[key] ?? translations.en[key];
}
