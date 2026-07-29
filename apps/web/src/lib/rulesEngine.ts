/**
 * Client-side symptom-to-disease rules engine.
 *
 * This is a direct TypeScript port of backend/app/modules/ussd/rules_engine.py,
 * kept intentionally identical so a farmer gets the same answer whether they
 * dial *123#, use the PWA offline, or use the native app. It is NOT the
 * on-device computer-vision model described in the PRD (Section 2, J3) —
 * that requires a trained TFLite model and labelled image data, which this
 * environment cannot produce. This rules engine covers the same 6 crop and
 * 7 livestock entries defined in the backend today; the PRD's claim of "30+
 * crop diseases, 12 livestock diseases" (Appendix A4) describes the target
 * coverage once Agritex/Vet Services populate the full decision tree — the
 * data model already supports arbitrary additions without a code change.
 */

export interface CropSymptomOption {
  code: string;
  label: string;
}

export interface CropTypeOption {
  code: string;
  label: string;
}

export const CROP_SYMPTOMS: CropSymptomOption[] = [
  { code: '1', label: 'Yellowing / discoloured leaves' },
  { code: '2', label: 'Wilting despite watering' },
  { code: '3', label: 'Chewed leaves / visible pests' },
  { code: '4', label: 'Grey or white powdery spots' },
  { code: '5', label: 'Stunted growth / weeds around roots' },
];

export const CROP_TYPES: CropTypeOption[] = [
  { code: '1', label: 'Maize' },
  { code: '2', label: 'Sorghum / Small grains' },
];

export const LIVESTOCK_SYMPTOMS: CropSymptomOption[] = [
  { code: '1', label: 'Skin nodules / lumps' },
  { code: '2', label: 'Coughing / laboured breathing' },
  { code: '3', label: 'Blisters on mouth or feet' },
  { code: '4', label: 'Lethargy / tick infestation' },
  { code: '5', label: 'Sudden death / bleeding from openings' },
];

export const ANIMAL_TYPES: CropTypeOption[] = [
  { code: '1', label: 'Cattle' },
  { code: '4', label: 'Poultry' },
];

interface CropRuleResult {
  disease1: string;
  disease2: string;
  action: string;
}

interface LivestockRuleResult {
  disease: string;
  action: string;
  notifiable?: boolean;
}

const CROP_RULES: Record<string, CropRuleResult> = {
  '1|1': { disease1: 'Maize Streak Virus', disease2: 'Nitrogen Deficiency',
    action: 'Remove infected plants. Apply fertiliser. Plant resistant varieties next season.' },
  '1|2': { disease1: 'Ergot', disease2: 'Leaf Rust',
    action: 'Remove infected heads. Apply recommended fungicide.' },
  '2|1': { disease1: 'Drought Stress', disease2: 'Root Rot',
    action: 'Check soil moisture. Improve drainage. Contact Agritex.' },
  '3|1': { disease1: 'Fall Armyworm', disease2: 'Spotted Stem Borer',
    action: 'Apply recommended pesticide within 24h. Check neighbouring fields.' },
  '4|1': { disease1: 'Gray Leaf Spot', disease2: 'Powdery Mildew',
    action: 'Apply fungicide. Improve air circulation. Rotate crops.' },
  '5|1': { disease1: 'Striga (Witchweed)', disease2: 'Soil Compaction',
    action: 'Hand-weed Striga. Apply herbicide. Use resistant varieties.' },
};

const LIVESTOCK_RULES: Record<string, LivestockRuleResult> = {
  '1|1': { disease: 'Lumpy Skin Disease',
    action: 'ISOLATE immediately. Vaccinate herd. Report to Vet Services 0800-VET.' },
  '2|1': { disease: 'Bovine Respiratory Disease',
    action: 'Isolate sick animals. Provide shelter. Contact Vet Services.' },
  '3|1': { disease: 'Foot and Mouth Disease',
    action: 'NOTIFIABLE: Restrict movement. Report to Vet Services immediately.', notifiable: true },
  '4|1': { disease: 'Anaplasmosis',
    action: 'Treat with tetracyclines per vet advice. Control ticks.' },
  '5|1': { disease: 'Anthrax',
    action: 'NOTIFIABLE EMERGENCY: Do not touch carcass. Call Vet Services NOW.', notifiable: true },
  '1|4': { disease: 'Fowl Pox',
    action: 'Vaccinate flock. Improve housing. Isolate affected birds.' },
  '2|4': { disease: 'Newcastle Disease',
    action: 'Vaccinate immediately. Cull severely affected birds. Disinfect housing.' },
};

export function diagnoseCrop(symptom: string, crop: string): CropRuleResult {
  return CROP_RULES[`${symptom}|${crop}`] ?? {
    disease1: 'Unknown condition',
    disease2: 'Possible nutrient deficiency',
    action: 'Contact your local Agritex officer for field assessment.',
  };
}

export function diagnoseLivestock(symptom: string, animal: string): LivestockRuleResult {
  return LIVESTOCK_RULES[`${symptom}|${animal}`] ?? {
    disease: 'Unknown condition',
    action: 'Contact Zimbabwe Veterinary Services for assessment. 0800-VET (free).',
  };
}
