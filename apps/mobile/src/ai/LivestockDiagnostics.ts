/**
 * On-device livestock disease diagnosis.
 * Vision model (<12MB) runs first.
 * Audio model (<3MB) runs ONLY if:
 *   - vision confidence < 0.75  AND
 *   - top disease class is tagged as "respiratory"
 */
import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import * as FileSystem from 'expo-file-system';
import type { DiagnosisResult, LivestockDiagnosisResult } from '@kohwai/shared/types';
import { AI_AUDIO_TRIGGER_GATE } from '@kohwai/shared/constants';

const RESPIRATORY_DISEASES = new Set([
  'Newcastle Disease', 'Bovine Respiratory Disease', 'Rabies',
  'Bovine Respiratory Syncytial Virus', 'Infectious Bronchitis',
]);

interface VisionRunResult {
  needsAudio: boolean;
  fullResult?: LivestockDiagnosisResult;
  visionResults: DiagnosisResult[];
  topConfidence: number;
  topIsRespiratory: boolean;
}

class LivestockDiagnostics {
  private visionModel: tf.GraphModel | null = null;
  private audioModel: tf.GraphModel | null  = null;
  private labels: string[] = [];

  async runVisionModel(imageBase64: string): Promise<VisionRunResult> {
    if (!this.visionModel) await this.loadVisionModel();
    const visionResults = await this.runVision(imageBase64);
    const top = visionResults[0];
    const topIsRespiratory = RESPIRATORY_DISEASES.has(top.disease);
    const needsAudio = top.confidence < AI_AUDIO_TRIGGER_GATE && topIsRespiratory;

    if (!needsAudio) {
      return {
        needsAudio: false,
        visionResults,
        topConfidence: top.confidence,
        topIsRespiratory,
        fullResult: {
          visionResults, audioResults: undefined, audioTriggered: false,
          overallConfidence: top.confidence,
          disclaimer: 'This is an AI-powered suggestion. Please verify with an Agritex officer before treatment.',
        },
      };
    }
    return { needsAudio: true, visionResults, topConfidence: top.confidence, topIsRespiratory };
  }

  async runAudioFusion(imageBase64: string, audioUri: string): Promise<LivestockDiagnosisResult> {
    const visionResults = await this.runVision(imageBase64);
    const audioResults  = await this.runAudio(audioUri);
    // Weighted fusion: 0.6 vision + 0.4 audio
    const overallConfidence = visionResults[0].confidence * 0.6 + (audioResults[0]?.confidence ?? 0) * 0.4;
    return {
      visionResults, audioResults, audioTriggered: true, overallConfidence,
      disclaimer: 'This is an AI-powered suggestion. Please verify with an Agritex officer before treatment.',
    };
  }

  private async runVision(imageBase64: string): Promise<DiagnosisResult[]> {
    const tensor = tf.tidy(() => {
      const raw = tf.util.encodeString(imageBase64, 'base64') as Uint8Array;
      const decoded = (tf as any).node?.decodeImage(raw) ?? tf.tensor(Array.from(raw));
      return decoded.resizeBilinear([224, 224]).expandDims(0).div(255.0);
    });
    const out = this.visionModel!.predict(tensor) as tf.Tensor;
    const probs = Array.from(await out.data() as Float32Array);
    tensor.dispose(); out.dispose();
    return this.topK(probs, 3).map((x, i) => ({
      rank: i + 1, disease: this.labels[x.idx] ?? `Class ${x.idx}`,
      confidence: x.val, treatmentAdvice: this.getTreatment(this.labels[x.idx]),
      isRespiratory: RESPIRATORY_DISEASES.has(this.labels[x.idx]),
    }));
  }

  private async runAudio(audioUri: string): Promise<DiagnosisResult[]> {
    if (!this.audioModel) await this.loadAudioModel();
    // TODO: Convert audio to mel-spectrogram tensor and run inference
    // Placeholder — replace with actual audio preprocessing
    return [{ rank:1, disease:'Healthy', confidence:0.5, treatmentAdvice:'Monitor closely.', isRespiratory:true }];
  }

  private topK(arr: number[], k: number) {
    return arr.map((val, idx) => ({ val, idx })).sort((a, b) => b.val - a.val).slice(0, k);
  }
  private getTreatment(disease: string): string {
    const t: Record<string, string> = {
      'Lumpy Skin Disease': 'Isolate animal immediately. Vaccinate herd. Contact Agritex Veterinary Services.',
      'Foot and Mouth Disease': 'Restrict animal movement. Report to Zimbabwe Veterinary Services immediately.',
      'Newcastle Disease': 'Vaccinate unaffected birds. Cull severely affected birds. Disinfect housing.',
    };
    return t[disease] ?? 'Consult a veterinarian or Agritex officer.';
  }

  private async loadVisionModel() {
    await tf.ready();
    const p = FileSystem.documentDirectory + 'models/livestock_vision.tflite';
    this.visionModel = await tf.loadGraphModel(`file://${p}`);
    const lj = await FileSystem.readAsStringAsync(FileSystem.documentDirectory + 'models/livestock_labels.json');
    this.labels = JSON.parse(lj);
  }
  private async loadAudioModel() {
    const p = FileSystem.documentDirectory + 'models/livestock_audio.tflite';
    this.audioModel = await tf.loadGraphModel(`file://${p}`);
  }
}

export const livestockDiagnostics = new LivestockDiagnostics();
