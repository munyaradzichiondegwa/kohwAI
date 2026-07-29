import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';

export default function ZundeScreen() {
  const nav = useNavigation<any>();
  return (
    <ScrollView style={s.c} contentContainerStyle={s.content}>
      <Text style={s.title}>🌾 Zunde — Agriculture</Text>
      <TouchableOpacity style={s.card} onPress={() => nav.navigate('CropDiag')}
        accessibilityRole="button" accessibilityLabel="Diagnose crop disease">
        <Text style={s.cardIcon}>🔍</Text>
        <View>
          <Text style={s.cardTitle}>AI Crop Diagnosis</Text>
          <Text style={s.cardSub}>Take a photo — offline AI identifies pests & diseases</Text>
        </View>
      </TouchableOpacity>
      <TouchableOpacity style={s.card} onPress={() => nav.navigate('LiveDiag')}
        accessibilityRole="button" accessibilityLabel="Diagnose livestock disease">
        <Text style={s.cardIcon}>🐄</Text>
        <View>
          <Text style={s.cardTitle}>Livestock AI Diagnosis</Text>
          <Text style={s.cardSub}>Vision + audio — offline, always free</Text>
        </View>
      </TouchableOpacity>
      {/* TODO: Planting Calendar, Weather Alerts, Advisory Cards */}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  c:       { flex:1, backgroundColor:'#f9fafb' },
  content: { padding:16 },
  title:   { fontSize:22, fontWeight:'700', color:'#111827', marginBottom:20 },
  card:    { flexDirection:'row', alignItems:'center', gap:16, backgroundColor:'#fff', borderRadius:16, padding:16, marginBottom:12, elevation:2 },
  cardIcon:  { fontSize:36 },
  cardTitle: { fontWeight:'600', fontSize:16, color:'#111827' },
  cardSub:   { fontSize:12, color:'#6b7280', marginTop:2 },
});
