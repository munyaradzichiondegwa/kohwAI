'use client';
import { useState, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { t, type Lang } from '@/i18n';
export function useLocale() {
  const user = useAuthStore(s => s.user);
  const [lang, setLang] = useState<Lang>((user?.language as Lang) || 'en');
  const translate = useCallback((key: Parameters<typeof t>[0]) => t(key, lang), [lang]);
  return { lang, setLang, t: translate };
}
