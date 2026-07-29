'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { getAlerts } from '@/lib/offline';
import type { Alert } from '@kohwai/shared/types';

const SEVERITY_CLASSES: Record<string, string> = {
  green:   'bg-brand-green  text-white',
  amber:   'bg-brand-amber  text-white',
  red:     'bg-brand-red    text-white',
  darkRed: 'bg-[#7B241C]   text-white',
  blue:    'bg-brand-blue   text-white',
};

export default function AlertCarousel() {
  const { data: alerts = [] } = useSWR<Alert[]>(
    'active-alerts',
    () => getAlerts(),
    { refreshInterval: 60_000 },
  );
  const [idx, setIdx] = useState(0);
  if (!alerts.length) return null;

  const alert = alerts[idx];
  return (
    <div className={`rounded-xl p-4 ${SEVERITY_CLASSES[alert.severity] || 'bg-gray-200'}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="font-semibold text-base">{alert.title}</p>
          <p className="text-sm opacity-90 mt-1">{alert.body}</p>
          <p className="text-xs opacity-70 mt-2">{alert.district} · {new Date(alert.createdAt).toLocaleDateString()}</p>
        </div>
        {alerts.length > 1 && (
          <div className="flex gap-1 ml-3">
            {alerts.map((_, i) => (
              <button key={i} onClick={() => setIdx(i)}
                className={`w-2 h-2 rounded-full ${i === idx ? 'bg-white' : 'bg-white/40'}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
