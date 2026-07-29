import { ScrollView, Text, View, StyleSheet, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';

const PILLARS = [
  { icon: '🌾', label: 'Zunde',    screen: 'Zunde',   color: '#1A7A4A' },
  { icon: '💧', label: 'Mvura',    screen: 'Mvura',   color: '#1A5276' },
  { icon: '☀️', label: 'Simba',    screen: 'Simba',   color: '#E8A020' },
  { icon: '🛒', label: 'Musika',   screen: 'Musika',  color: '#5D6D7E' },
  { icon: '🐄', label: 'Livestock',screen: 'LiveDiag',color: '#784212' },
];

export default function DashboardScreen() {
  const nav = useNavigation<any>();
  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      <Text style={s.greeting}>Good morning 👋</Text>
      <Text style={s.subtitle}>Your farm intelligence dashboard</Text>
      <View style={s.grid}>
        {PILLARS.map(p => (
          <TouchableOpacity key={p.label} style={[s.card, { borderLeftColor: p.color }]}
            onPress={() => nav.navigate(p.screen)}
            accessibilityRole="button" accessibilityLabel={`Open ${p.label}`}>
            <Text style={s.cardIcon}>{p.icon}</Text>
            <Text style={s.cardLabel}>{p.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:'#f9fafb' },
  content:   { padding:16 },
  greeting:  { fontSize:22, fontWeight:'700', color:'#111827' },
  subtitle:  { fontSize:14, color:'#6b7280', marginBottom:24 },
  grid:      { flexDirection:'row', flexWrap:'wrap', gap:12 },
  card:      { width:'47%', backgroundColor:'#fff', borderRadius:16, padding:16, borderLeftWidth:4, elevation:2, shadowColor:'#000', shadowOpacity:0.05, shadowRadius:4 },
  cardIcon:  { fontSize:32, marginBottom:8 },
  cardLabel: { fontWeight:'600', color:'#111827' },
});
