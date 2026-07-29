/**
 * OTA model updater — checks for new TFLite models on S3 and downloads them.
 * Runs on app launch AND silently every 24-48h via BackgroundFetch.
 */
import * as FileSystem from 'expo-file-system';
import * as BackgroundFetch from 'expo-background-fetch';
import * as TaskManager from 'expo-task-manager';

const OTA_CHECK_URL = process.env.EXPO_PUBLIC_API_URL + '/api/v1/models/ota/latest';
const MODEL_DIR     = FileSystem.documentDirectory + 'models/';
const TASK_NAME     = 'KOHWAI_MODEL_UPDATE';

interface OTAManifest {
  cropVision:       { version: string; url: string; checksum: string };
  livestockVision:  { version: string; url: string; checksum: string };
  livestockAudio:   { version: string; url: string; checksum: string };
  cropLabels:       { version: string; url: string };
  livestockLabels:  { version: string; url: string };
}

TaskManager.defineTask(TASK_NAME, async () => {
  try { await otaModelUpdater.checkForUpdates(); return BackgroundFetch.BackgroundFetchResult.NewData; }
  catch { return BackgroundFetch.BackgroundFetchResult.Failed; }
});

class OTAModelUpdater {
  async registerBackgroundTask() {
    await BackgroundFetch.registerTaskAsync(TASK_NAME, {
      minimumInterval: 24 * 60 * 60, // 24 hours
      stopOnTerminate: false,
      startOnBoot: true,
    });
  }

  async checkForUpdates(): Promise<void> {
    const res = await fetch(OTA_CHECK_URL);
    if (!res.ok) return;
    const manifest: OTAManifest = await res.json();
    await FileSystem.makeDirectoryAsync(MODEL_DIR, { intermediates: true });

    const tasks = [
      { key: 'cropVision',      dest: MODEL_DIR + 'crop_vision.tflite'      },
      { key: 'livestockVision', dest: MODEL_DIR + 'livestock_vision.tflite' },
      { key: 'livestockAudio',  dest: MODEL_DIR + 'livestock_audio.tflite'  },
      { key: 'cropLabels',      dest: MODEL_DIR + 'crop_labels.json'        },
      { key: 'livestockLabels', dest: MODEL_DIR + 'livestock_labels.json'   },
    ] as const;

    for (const task of tasks) {
      const m = manifest[task.key] as any;
      if (!m?.url) continue;
      const versionFile = MODEL_DIR + task.key + '.version';
      let currentVersion = '';
      try { currentVersion = await FileSystem.readAsStringAsync(versionFile); } catch {}
      if (currentVersion === m.version) continue; // Already up to date
      await FileSystem.downloadAsync(m.url, task.dest);
      if (m.version) await FileSystem.writeAsStringAsync(versionFile, m.version);
    }
  }
}

export const otaModelUpdater = new OTAModelUpdater();
