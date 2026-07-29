'use client';
import { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { apiClient } from '@/lib/api';
import { db } from '@/lib/db';
import { LIVESTOCK_SYMPTOMS, ANIMAL_TYPES, diagnoseLivestock } from '@/lib/rulesEngine';

type DiagResult = { disease: string; action: string; notifiable: boolean; source: 'server' | 'offline' };

export default function LivestockPage() {
  const [animalCode, setAnimalCode] = useState<string | null>(null);
  const [result, setResult] = useState<DiagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [animals, setAnimals] = useState<any[]>([]);
  const [showRegister, setShowRegister] = useState(false);
  const [newName, setNewName] = useState('');

  useEffect(() => { apiClient.get('/livestock/profiles').then(r => setAnimals(r.data)).catch(() => {}); }, []);

  async function runDiagnosis(animal: string, symptom: string) {
    setLoading(true);
    try {
      const res = await apiClient.post('/livestock/diagnose', { animal_type_code: animal, symptom_code: symptom });
      setResult({ disease: res.data.disease, action: res.data.action, notifiable: res.data.notifiable, source: 'server' });
    } catch {
      const local = diagnoseLivestock(symptom, animal);
      setResult({ disease: local.disease, action: local.action, notifiable: !!local.notifiable, source: 'offline' });
      await db.diagnosisQueue.add({
        kind: 'livestock', animalType: animal, symptom, disease1: local.disease, action: local.action,
        createdAt: new Date().toISOString(), synced: false,
      });
    } finally { setLoading(false); }
  }

  async function registerAnimal() {
    if (!newName.trim()) return;
    try {
      const res = await apiClient.post('/livestock/profiles', {
        name: newName, animal_type: animalCode === '4' ? 'poultry' : 'cattle',
      });
      setAnimals(a => [...a, res.data]);
    } catch { /* offline: registration requires a synced profile, so we just clear the form */ }
    setNewName(''); setShowRegister(false);
  }

  return (
    <AppShell title="Livestock Health">
      <section className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">🐄 Livestock symptom checker</h1>
        <p className="text-sm text-gray-500 mt-1">Works offline. Confirm with Zimbabwe Veterinary Services (0800-VET, free).</p>
      </section>

      {!result && (
        <>
          <section className="mb-6">
            <h2 className="font-semibold text-gray-800 mb-2">1. Which animal?</h2>
            <div className="grid grid-cols-2 gap-2">
              {ANIMAL_TYPES.map(a => (
                <button key={a.code} onClick={() => setAnimalCode(a.code)}
                  className={`p-3 rounded-xl border text-sm font-medium ${
                    animalCode === a.code ? 'bg-brand-green text-white border-brand-green' : 'bg-white border-gray-200'
                  }`}>
                  {a.label}
                </button>
              ))}
            </div>
          </section>

          {animalCode && (
            <section className="mb-6">
              <h2 className="font-semibold text-gray-800 mb-2">2. What are you seeing?</h2>
              <div className="flex flex-col gap-2">
                {LIVESTOCK_SYMPTOMS.map(s => (
                  <button key={s.code} onClick={() => runDiagnosis(animalCode, s.code)}
                    className="p-3 rounded-xl border border-gray-200 bg-white text-sm text-left hover:border-brand-green">
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
        <section className={`mb-6 rounded-2xl border p-4 ${result.notifiable ? 'bg-red-50 border-red-300' : 'bg-white border-gray-100'}`}>
          {result.notifiable && (
            <p className="text-xs font-bold text-brand-red uppercase mb-2">⚠ Notifiable disease — report immediately</p>
          )}
          <h2 className="font-bold text-gray-900 mb-2">{result.disease}</h2>
          <div className="bg-brand-amber/10 border border-brand-amber/30 rounded-lg p-3 text-sm text-gray-800">
            <strong>Recommended action:</strong> {result.action}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            This is a symptom guide, not an AI diagnosis. Confirm with Zimbabwe Veterinary Services.
          </p>
          <button onClick={() => setResult(null)} className="mt-4 w-full border border-gray-300 rounded-xl py-2 text-sm font-medium">
            Check again
          </button>
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-800">My animals</h2>
          <button onClick={() => setShowRegister(v => !v)} className="text-sm text-brand-green font-medium">+ Add</button>
        </div>
        {showRegister && (
          <div className="flex gap-2 mb-3">
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Animal name"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            <button onClick={registerAnimal} className="bg-brand-green text-white rounded-lg px-4 text-sm font-medium">Save</button>
          </div>
        )}
        {animals.length === 0 && <p className="text-sm text-gray-400">No animals registered yet.</p>}
        <div className="flex flex-col gap-2">
          {animals.map(a => (
            <div key={a.id} className="bg-white rounded-xl border border-gray-100 p-3 flex justify-between items-center">
              <div>
                <p className="font-medium text-gray-900">{a.name}</p>
                <p className="text-xs text-gray-500">{a.animal_type}{a.breed ? ` · ${a.breed}` : ''}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                a.health_status === 'sick' ? 'bg-brand-red/10 text-brand-red' : 'bg-brand-green/10 text-brand-green'
              }`}>{a.health_status}</span>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
