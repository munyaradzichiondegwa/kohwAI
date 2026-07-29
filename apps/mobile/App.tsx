import 'react-native-gesture-handler';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import AppNavigator from './src/navigation/AppNavigator';
import { otaModelUpdater } from './src/ai/OTAModelUpdater';

export default function App() {
  useEffect(() => {
    // Check for AI model updates in background
    otaModelUpdater.checkForUpdates().catch(console.error);
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="light" backgroundColor="#1A7A4A" />
      <AppNavigator />
    </SafeAreaProvider>
  );
}
