/**
 * On-device TFLite crop pest & disease classification.
 * Model: < 10MB, < 5s inference, fully offline.
 * Phase 2 feature — model loaded from OTA bundle.
 */
import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import * as FileSystem from 'expo-file-system';
import type { DiagnosisResult } from '@kohwai/shared/types';
import { AI_CONFIDENCE_GATE } from '@kohwai/shared/constants';

const MODEL_PATH = FileSystem.documentDirectory + 'models/crop_vision.tflite';
const LABELS_PATH = FileSystem.documentDirectory + 'models/crop_labels.json';

class CropDiagnostics {
  private model: tf.GraphModel | null = null;
  private labels: string[] = [];

  async loadModel(): Promise<void> {
    const modelExists = (await FileSystem.getInfoAsync(MODEL_PATH)).exists;
    if (!modelExists) throw new Error('Crop model not downloaded. Please connect to the internet.');
    await tf.ready();
    this.model = await tf.loadGraphModel(`file://${MODEL_PATH}`);
    const labelsJson = await FileSystem.readAsStringAsync(LABELS_PATH);
    this.labels = JSON.parse(labelsJson);
  }

  async diagnose(imageBase64: string): Promise<DiagnosisResult[]> {
    if (!this.model) await this.loadModel();
    // Preprocess: decode base64 → tensor [1, 224, 224, 3]
    const imageTensor = tf.tidy(() => {
      const raw = tf.util.encodeString(imageBase64, 'base64') as Uint8Array;
      const decoded = tf.node ? (tf.node as any).decodeImage(raw) : tf.tensor(Array.from(raw));
      return decoded.resizeBilinear([224, 224]).expandDims(0).div(255.0);
    });

    const predictions = this.model!.predict(imageTensor) as tf.Tensor;
    const probs = await predictions.data() as Float32Array;
    imageTensor.dispose(); predictions.dispose();

    // Top-3
    const indexed = Array.from(probs).map((p, i) => ({ p, i }));
    indexed.sort((a, b) => b.p - a.p);
    const top3 = indexed.slice(0, 3);

    return top3.map((item, rank) => ({
      rank:           rank + 1,
      disease:        this.labels[item.i] ?? `Class ${item.i}`,
      confidence:     item.p,
      treatmentAdvice: this.getTreatment(this.labels[item.i]),
      isRespiratory:  false,
    }));
  }

  private getTreatment(disease: string): string {
    // TODO: Load from Agritex advisory JSON
    const treatments: Record<string, string> = {
      'Fall Armyworm': 'Apply recommended pesticide within 24h. Contact Agritex for approved products.',
      'Maize Streak Virus': 'Remove infected plants. Plant resistant varieties next season.',
      'Gray Leaf Spot': 'Apply fungicide. Improve air circulation. Rotate crops.',
    };
    return treatments[disease] ?? 'Consult your local Agritex officer for treatment advice.';
  }

  isLowConfidence(results: DiagnosisResult[]): boolean {
    return results.length === 0 || results[0].confidence < AI_CONFIDENCE_GATE;
  }
}

export const cropDiagnostics = new CropDiagnostics();
