/**
 * Client-side symptom triage for offline use. Reads shared/rules/rules.json, which is GENERATED from the
 * Python rules engine (backend/scripts/export_rules.py) — so USSD, the API and the offline app always agree.
 * A backend test fails if the JSON is stale.
 *
 * Content is NOT yet signed off by Agritex / Veterinary Services. Helpline numbers are never hardcoded:
 * set NEXT_PUBLIC_VET_CONTACT / NEXT_PUBLIC_AGRITEX_CONTACT once real numbers are confirmed.
 */
import rules from '@kohwai/shared/rules/rules.json';

export interface Option { code: string; label: string }

export const CROP_SYMPTOMS: Option[] = rules.cropSymptoms.map(({ code, label }) => ({ code, label }));
export const CROP_TYPES: Option[] = rules.cropTypes;
export const LIVESTOCK_SYMPTOMS: Option[] = rules.livestockSymptoms.map(({ code, label }) => ({ code, label }));
export const ANIMAL_TYPES: Option[] = rules.animalTypes;

const vet = () => (process.env.NEXT_PUBLIC_VET_CONTACT ? `Vet Services ${process.env.NEXT_PUBLIC_VET_CONTACT}` : 'your nearest Veterinary office');
const agritex = () => (process.env.NEXT_PUBLIC_AGRITEX_CONTACT ? `Agritex ${process.env.NEXT_PUBLIC_AGRITEX_CONTACT}` : 'your Agritex officer');

export interface CropRuleResult { disease1: string; disease2: string | null; action: string; known: boolean }
export interface LivestockRuleResult { disease: string; action: string; notifiable: boolean; known: boolean }

const CROP_RULES = rules.cropRules as Record<string, { disease1: string; disease2: string; action: string }>;
const LIVESTOCK_RULES = rules.livestockRules as Record<string, { disease: string; action: string; notifiable: boolean }>;

export function diagnoseCrop(symptom: string, crop: string): CropRuleResult {
  const r = CROP_RULES[`${symptom}|${crop}`];
  if (r) return { ...r, known: true };
  return { disease1: 'Unknown condition', disease2: null, known: false,
           action: `No guidance for this combination yet. Contact ${agritex()} for a field assessment.` };
}

export function diagnoseLivestock(symptom: string, animal: string): LivestockRuleResult {
  const r = LIVESTOCK_RULES[`${symptom}|${animal}`];
  if (r) return { ...r, action: r.action.replaceAll('{vet}', vet()), known: true };
  return { disease: 'Unknown condition', notifiable: false, known: false,
           action: `No guidance for this combination yet. Contact ${vet()} for assessment.` };
}
