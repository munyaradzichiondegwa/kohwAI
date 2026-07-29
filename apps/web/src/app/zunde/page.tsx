'use client';
import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import ConfidenceBar from '@/components/ui/ConfidenceBar';
import { apiClient } from '@/lib/api';
import { db } from '@/lib/db';
import { CROP_SYMPTOMS, CROP_TYPES, diagnoseCrop } from '@/lib/rulesEngine';
import { useAuthStore } from '@/stores/authStore';

type DiagResult = { disease1: string; disease2: string; action: string; source: 'server' | 'offline' };

export default function ZundePage() {
  const user = useAuthStore(s => s.user);
  const [cropCode, setCropCode] = useState<string | null>(null);
  const [symptomCode, setSymptomCode] = useState<string | null>(null);
  const [result, setResult] = useState<DiagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [pestReported, setPestReported] = useState(false);
  const [calendar, setCalendar] = useState<any>(null);
  const [calendarLoading, setCalendarLoading] = useState(false);

  async function runDiagnosis(crop: string, symptom: string) {
    setLoading(true);
    try {
      const res = await apiClient.post('/zunde/diagnose', { crop_type_code: crop, symptom_code: symptom });
      setResult({
        disease1: res.data.top_disease, disease2: res.data.second_disease,
        action: res.data.action, source: 'server',
      });
    } catch {
      const local = diagnoseCrop(symptom, crop);
      setResult({ disease1: local.disease1, disease2: local.disease2, action: local.action, source: 'offline' });
      await db.diagnosisQueue.add({
        kind: 'crop', cropType: crop, symptom, disease1: local.disease1, disease2: local.disease2,
        action: local.action, createdAt: new Date().toISOString(), synced: false,
      });
    } finally {
      setLoading(false);
    }
  }

  async function reportPest() {
    if (!result) return;
    try {
      await apiClient.post('/zunde/pest-sightings', {
        species: result.disease1, severity: 'medium', district: user?.district || 'Harare',
      });
    } catch { /* already queued offline via diagnosisQueue when the diagnosis itself was offline */ }
    setPestReported(true);
  }

  async function loadCalendar() {
    setCalendarLoading(true);
    try {
      const res = await apiClient.get(`/zunde/planting-calendar?district=${user?.district || 'Harare'}`);
      setCalendar(res.data);
    } catch {
      setCalendar({ error: true });
    } finally {
      setCalendarLoading(false);
    }
  }

  function reset() {
    setCropCode(null); setSymptomCode(null); setResult(null); setPestReported(false);
  }

  return (
    <AppShell title="Zunde — Agriculture">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">🌾 Crop symptom checker</h1>
        <p className="text-sm text-gray-500 mt-1">
          Works offline. This is a symptom guide, not an AI diagnosis — always confirm with Agritex.
        </p>
      </section>

      {!result && (
        <>
          <section className="mb-6">
            <h2 className="font-semibold text-gray-800 mb-2">1. What are you growing?</h2>
            <div className="grid grid-cols-2 gap-2">
              {CROP_TYPES.map(c => (
                <button key={c.code} onClick={() => setCropCode(c.code)}
                  className={`p-3 rounded-xl border text-sm font-medium text-left transition-colors ${
                    cropCode === c.code ? 'bg-brand-green text-white border-brand-green' : 'bg-white border-gray-200'
                  }`}>
                  {c.label}
                </button>
              ))}
            </div>
          </section>

          {cropCode && (
            <section className="mb-6">
              <h2 className="font-semibold text-gray-800 mb-2">2. What do you see?</h2>
              <div className="flex flex-col gap-2">
                {CROP_SYMPTOMS.map(s => (
                  <button key={s.code}
                    onClick={() => { setSymptomCode(s.code); runDiagnosis(cropCode, s.code); }}
                    className="p-3 rounded-xl border border-gray-200 bg-white text-sm text-left hover:border-brand-green"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          {loading && <p className="text-sm text-gray-500">Checking…</p>}
        </>
      )}

      {result && (
        <section className="mb-6 bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-gray-900">Most likely: {result.disease1}</h2>
            {result.source === 'offline' && (
              <span className="text-xs bg-brand-blue/10 text-brand-blue px-2 py-0.5 rounded-full">Saved offline</span>
            )}
          </div>
          <ConfidenceBar label={result.disease1} confidence={0.7} />
          {result.disease2 && <ConfidenceBar label={`Also possible: ${result.disease2}`} confidence={0.35} />}
          <div className="bg-brand-amber/10 border border-brand-amber/30 rounded-lg p-3 mt-3 text-sm text-gray-800">
            <strong>Recommended action:</strong> {result.action}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            This is a symptom guide, not an AI diagnosis. Confirm with your local Agritex officer.
          </p>
          <div className="flex gap-2 mt-4">
            <button onClick={reportPest} disabled={pestReported}
              className="flex-1 bg-brand-red text-white rounded-xl py-2 text-sm font-medium disabled:opacity-50">
              {pestReported ? 'Reported ✓' : 'Report to community'}
            </button>
            <button onClick={reset} className="flex-1 border border-gray-300 rounded-xl py-2 text-sm font-medium">
              Check again
            </button>
          </div>
        </section>
      )}

      <section className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-800">🌧️ Rains &amp; planting guidance</h2>
          {!calendar && (
            <button onClick={loadCalendar} disabled={calendarLoading}
              className="text-sm text-brand-green font-medium disabled:opacity-50">
              {calendarLoading ? 'Loading…' : 'Check'}
            </button>
          )}
        </div>
        {calendar && !calendar.error && (
          <div className="bg-white rounded-2xl border border-gray-100 p-4 text-sm">
            <p className="text-gray-800">{calendar.guidance}</p>
            <p className="text-xs text-gray-400 mt-2">Source: {calendar.data_source}</p>
            <p className="text-xs text-gray-400 mt-1">{calendar.disclaimer}</p>
          </div>
        )}
        {calendar?.error && (
          <p className="text-sm text-gray-500">Couldn't reach satellite data right now — try again once online.</p>
        )}
      </section>
    </AppShell>
  );
}
