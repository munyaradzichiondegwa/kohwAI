import { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { Camera, CameraView } from 'expo-camera';
import { cropDiagnostics } from '../../ai/CropDiagnostics';
import type { DiagnosisResult } from '@kohwai/shared/types';

const DISCLAIMER = 'This is an AI-powered suggestion. Please verify with an Agritex officer before treatment.';

export default function CropDiagnosisScreen() {
  const [permission, requestPermission] = Camera.useCameraPermissions();
  const [results, setResults]   = useState<DiagnosisResult[] | null>(null);
  const [loading, setLoading]   = useState(false);
  const cameraRef = useRef<CameraView>(null);

  async function capture() {
    if (!cameraRef.current) return;
    setLoading(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ base64: true, quality: 0.7 });
      if (!photo?.base64) return;
      const res = await cropDiagnostics.diagnose(photo.base64);
      setResults(res);
    } catch (e) {
      Alert.alert('Error', 'Could not process image. Please try again.');
    } finally { setLoading(false); }
  }

  if (!permission?.granted) {
    return (
      <View style={s.center}>
        <Text style={s.msg}>Camera access needed for crop diagnosis</Text>
        <TouchableOpacity style={s.btn} onPress={requestPermission}><Text style={s.btnTxt}>Grant Access</Text></TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={s.container}>
      {!results ? (
        <>
          <CameraView ref={cameraRef} style={s.camera} facing="back" />
          <TouchableOpacity style={s.captureBtn} onPress={capture} disabled={loading}
            accessibilityRole="button" accessibilityLabel="Take photo for crop diagnosis">
            <Text style={s.captureTxt}>{loading ? 'Analysing…' : '📷  Diagnose Crop'}</Text>
          </TouchableOpacity>
        </>
      ) : (
        <ScrollView style={s.results} contentContainerStyle={{ padding:20 }}>
          <Text style={s.heading}>Diagnosis Results</Text>
          {results.map((r, i) => (
            <View key={i} style={s.result}>
              <Text style={s.rank}>#{r.rank} — {r.disease}</Text>
              <View style={s.bar}><View style={[s.fill, { width: `${Math.round(r.confidence*100)}%`, backgroundColor: r.confidence >= 0.7 ? '#1A7A4A' : '#E8A020' }]} /></View>
              <Text style={s.conf}>{Math.round(r.confidence*100)}% confidence</Text>
              <Text style={s.advice}>{r.treatmentAdvice}</Text>
            </View>
          ))}
          <Text style={s.disclaimer}>{DISCLAIMER}</Text>
          <TouchableOpacity style={s.retakeBtn} onPress={() => setResults(null)}>
            <Text style={s.btnTxt}>📷 Take Another</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container:  { flex:1, backgroundColor:'#000' },
  camera:     { flex:1 },
  center:     { flex:1, alignItems:'center', justifyContent:'center', padding:24 },
  msg:        { fontSize:16, color:'#374151', textAlign:'center', marginBottom:16 },
  captureBtn: { position:'absolute', bottom:32, alignSelf:'center', backgroundColor:'#1A7A4A', borderRadius:40, paddingHorizontal:32, paddingVertical:16 },
  captureTxt: { color:'#fff', fontSize:18, fontWeight:'600' },
  results:    { flex:1, backgroundColor:'#f9fafb' },
  heading:    { fontSize:22, fontWeight:'700', color:'#111827', marginBottom:16 },
  result:     { backgroundColor:'#fff', borderRadius:12, padding:16, marginBottom:12 },
  rank:       { fontWeight:'700', fontSize:16, marginBottom:8 },
  bar:        { height:8, backgroundColor:'#e5e7eb', borderRadius:4, overflow:'hidden', marginBottom:4 },
  fill:       { height:'100%', borderRadius:4 },
  conf:       { fontSize:12, color:'#6b7280' },
  advice:     { fontSize:14, color:'#374151', marginTop:8 },
  disclaimer: { fontSize:12, color:'#9ca3af', fontStyle:'italic', marginVertical:16 },
  btn:        { backgroundColor:'#1A7A4A', borderRadius:12, padding:14, alignItems:'center' },
  retakeBtn:  { backgroundColor:'#374151', borderRadius:12, padding:14, alignItems:'center', marginBottom:32 },
  btnTxt:     { color:'#fff', fontWeight:'600', fontSize:16 },
});
