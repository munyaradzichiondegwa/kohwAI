import { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { Camera, CameraView } from 'expo-camera';
import { Audio } from 'expo-av';
import { livestockDiagnostics } from '../../ai/LivestockDiagnostics';
import type { LivestockDiagnosisResult } from '@kohwai/shared/types';

const DISCLAIMER = 'This is an AI-powered suggestion. Please verify with an Agritex officer before treatment.';

type Step = 'camera' | 'audio_prompt' | 'recording' | 'results';

export default function LivestockDiagnosisScreen() {
  const [camPerm, requestCamPerm] = Camera.useCameraPermissions();
  const [step, setStep]     = useState<Step>('camera');
  const [results, setResults] = useState<LivestockDiagnosisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [photoB64, setPhotoB64] = useState<string | null>(null);
  const cameraRef = useRef<CameraView>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);

  async function capturePhoto() {
    if (!cameraRef.current) return;
    setLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ base64:true, quality:0.7 });
      if (!photo?.base64) return;
      setPhotoB64(photo.base64);
      const visionResult = await livestockDiagnostics.runVisionModel(photo.base64);
      if (visionResult.needsAudio) {
        setStep('audio_prompt');
      } else {
        setResults(visionResult.fullResult!);
        setStep('results');
      }
    } catch { Alert.alert('Error', 'Could not process image.'); }
    finally { setLoading(false); }
  }

  async function startRecording() {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) { Alert.alert('Microphone access required'); return; }
    const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
    recordingRef.current = recording;
    setStep('recording');
    setTimeout(() => stopRecording(), 3000); // Auto-stop after 3s
  }

  async function stopRecording() {
    if (!recordingRef.current || !photoB64) return;
    setLoading(true);
    await recordingRef.current.stopAndUnloadAsync();
    const uri = recordingRef.current.getURI();
    try {
      const finalResult = await livestockDiagnostics.runAudioFusion(photoB64, uri!);
      setResults(finalResult);
      setStep('results');
    } catch { Alert.alert('Error', 'Audio analysis failed. Showing vision results.'); }
    finally { setLoading(false); }
  }

  if (!camPerm?.granted) {
    return (
      <View style={s.center}>
        <Text style={s.msg}>Camera access needed for livestock diagnosis</Text>
        <TouchableOpacity style={s.btn} onPress={requestCamPerm}><Text style={s.btnTxt}>Grant Access</Text></TouchableOpacity>
      </View>
    );
  }

  if (step === 'camera') return (
    <View style={s.container}>
      <CameraView ref={cameraRef} style={s.camera} facing="back" />
      <Text style={s.hint}>Hold phone 30cm from the animal</Text>
      <TouchableOpacity style={s.captureBtn} onPress={capturePhoto} disabled={loading}
        accessibilityRole="button" accessibilityLabel="Take livestock photo">
        <Text style={s.captureTxt}>{loading ? 'Analysing…' : '📷  Diagnose Animal'}</Text>
      </TouchableOpacity>
    </View>
  );

  if (step === 'audio_prompt') return (
    <View style={s.center}>
      <Text style={s.heading}>🎙️ Audio Analysis Needed</Text>
      <Text style={s.msg}>Vision confidence is low for a respiratory condition.{'
'}Hold your phone 20cm from the animal and record a 3-second sound.</Text>
      <TouchableOpacity style={s.btn} onPress={startRecording}><Text style={s.btnTxt}>Start Recording</Text></TouchableOpacity>
    </View>
  );

  if (step === 'recording') return (
    <View style={s.center}>
      <Text style={[s.heading, {color:'#C0392B'}]}>🔴 Recording…</Text>
      <Text style={s.msg}>Recording will stop automatically after 3 seconds.</Text>
    </View>
  );

  if (step === 'results' && results) return (
    <ScrollView style={{flex:1, backgroundColor:'#f9fafb'}} contentContainerStyle={{padding:20}}>
      <Text style={s.heading}>Livestock Diagnosis Results</Text>
      {results.audioTriggered && <Text style={s.audioNote}>🎙️ Audio analysis included</Text>}
      {results.visionResults.map((r, i) => (
        <View key={i} style={s.result}>
          <Text style={s.rank}>#{r.rank} — {r.disease}</Text>
          <View style={s.bar}><View style={[s.fill, {width:`${Math.round(r.confidence*100)}%`, backgroundColor:'#1A7A4A'}]} /></View>
          <Text style={s.conf}>{Math.round(r.confidence*100)}% confidence</Text>
          <Text style={s.advice}>{r.treatmentAdvice}</Text>
        </View>
      ))}
      <Text style={s.disclaimer}>{DISCLAIMER}</Text>
      <TouchableOpacity style={s.btn} onPress={() => setStep('camera')}>
        <Text style={s.btnTxt}>📷 Diagnose Another</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  return null;
}

const s = StyleSheet.create({
  container:  { flex:1, backgroundColor:'#000' },
  camera:     { flex:1 },
  center:     { flex:1, alignItems:'center', justifyContent:'center', padding:24, backgroundColor:'#f9fafb' },
  heading:    { fontSize:22, fontWeight:'700', color:'#111827', marginBottom:12 },
  msg:        { fontSize:15, color:'#374151', textAlign:'center', lineHeight:22, marginBottom:24 },
  hint:       { position:'absolute', top:60, alignSelf:'center', color:'#fff', backgroundColor:'rgba(0,0,0,0.5)', padding:8, borderRadius:8, fontSize:14 },
  captureBtn: { position:'absolute', bottom:32, alignSelf:'center', backgroundColor:'#1A7A4A', borderRadius:40, paddingHorizontal:32, paddingVertical:16 },
  captureTxt: { color:'#fff', fontSize:18, fontWeight:'600' },
  result:     { backgroundColor:'#fff', borderRadius:12, padding:16, marginBottom:12 },
  rank:       { fontWeight:'700', fontSize:16, marginBottom:8 },
  bar:        { height:8, backgroundColor:'#e5e7eb', borderRadius:4, overflow:'hidden', marginBottom:4 },
  fill:       { height:'100%', borderRadius:4 },
  conf:       { fontSize:12, color:'#6b7280' },
  advice:     { fontSize:14, color:'#374151', marginTop:8 },
  audioNote:  { backgroundColor:'#EBF5FB', borderRadius:8, padding:10, marginBottom:12, color:'#1A5276', fontSize:14 },
  disclaimer: { fontSize:12, color:'#9ca3af', fontStyle:'italic', marginVertical:16 },
  btn:        { backgroundColor:'#1A7A4A', borderRadius:12, padding:14, alignItems:'center', marginBottom:16 },
  btnTxt:     { color:'#fff', fontWeight:'600', fontSize:16 },
});
