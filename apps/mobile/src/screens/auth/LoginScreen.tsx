import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { useAuthStore } from '../../stores/authStore';
import { apiClient } from '../../services/api';

export default function LoginScreen() {
  const setAuth = useAuthStore(s => s.setAuth);
  const [phone, setPhone] = useState('');
  const [otp, setOtp]     = useState('');
  const [step, setStep]   = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  async function requestOtp() {
    setLoading(true); setError('');
    try { await apiClient.post('/auth/otp/request', { phone }); setStep('otp'); }
    catch (e: any) { setError(e?.message || 'Failed to send OTP'); }
    finally { setLoading(false); }
  }

  async function verifyOtp() {
    setLoading(true); setError('');
    try {
      const res = await apiClient.post('/auth/otp/verify', { phone, otp });
      setAuth(res.data.access_token, res.data.refresh_token, res.data.user);
    } catch (e: any) { setError(e?.message || 'Invalid OTP'); }
    finally { setLoading(false); }
  }

  return (
    <View style={s.container}>
      <Text style={s.logo}>🌿</Text>
      <Text style={s.title}>KohwAI</Text>
      <Text style={s.subtitle}>Climate Resilience Super-App</Text>
      {!!error && <Text style={s.error}>{error}</Text>}
      {step === 'phone' ? (
        <>
          <TextInput style={s.input} placeholder="+263 7X XXX XXXX"
            keyboardType="phone-pad" value={phone}
            onChangeText={setPhone} accessibilityLabel="Phone number input" />
          <TouchableOpacity style={s.btn} onPress={requestOtp} disabled={loading || !phone}
            accessibilityRole="button" accessibilityLabel="Send OTP">
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Send OTP</Text>}
          </TouchableOpacity>
        </>
      ) : (
        <>
          <TextInput style={s.input} placeholder="6-digit OTP"
            keyboardType="number-pad" maxLength={6} value={otp}
            onChangeText={setOtp} accessibilityLabel="OTP input" />
          <TouchableOpacity style={s.btn} onPress={verifyOtp} disabled={loading || otp.length < 6}
            accessibilityRole="button" accessibilityLabel="Verify OTP">
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Verify & Login</Text>}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setStep('phone')}>
            <Text style={s.link}>← Change number</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, alignItems:'center', justifyContent:'center', padding:24, backgroundColor:'#f9fafb' },
  logo:      { fontSize:56 },
  title:     { fontSize:28, fontWeight:'700', color:'#1A7A4A', marginTop:8 },
  subtitle:  { fontSize:14, color:'#6b7280', marginBottom:32 },
  error:     { color:'#C0392B', marginBottom:12 },
  input:     { width:'100%', borderWidth:1, borderColor:'#d1d5db', borderRadius:12, padding:14, marginBottom:14, fontSize:16, backgroundColor:'#fff' },
  btn:       { width:'100%', backgroundColor:'#1A7A4A', borderRadius:12, padding:14, alignItems:'center' },
  btnText:   { color:'#fff', fontWeight:'600', fontSize:16 },
  link:      { marginTop:16, color:'#6b7280', fontSize:14 },
});
