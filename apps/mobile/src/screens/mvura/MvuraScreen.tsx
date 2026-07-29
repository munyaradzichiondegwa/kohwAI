import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';

export default function MvuraScreen() {
  return (
    <ScrollView style={s.c} contentContainerStyle={s.content}>
      <Text style={s.title}>💧 Mvura — Water Security</Text>
      {/* TODO: Implement borehole map with MapLibre GL */}
      <View style={s.card}>
        <Text style={s.cardTitle}>🗺️ Borehole Map</Text>
        <Text style={s.cardSub}>Map of working boreholes within 50km — offline cached</Text>
      </View>
      <View style={s.card}>
        <Text style={s.cardTitle}>📍 Nearest Borehole</Text>
        <Text style={s.cardSub}>Feature phone? Dial *123# → 2 → 1</Text>
      </View>
      <View style={s.card}>
        <Text style={s.cardTitle}>💡 Smart Irrigation Tips</Text>
        <Text style={s.cardSub}>Based on your crop type and Zunde rainfall forecast</Text>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  c:       { flex: 1, backgroundColor: '#f9fafb' },
  content: { padding: 16 },
  title:   { fontSize: 22, fontWeight: '700', color: '#111827', marginBottom: 20 },
  card:    { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 12, elevation: 2 },
  cardTitle:{ fontWeight: '600', fontSize: 16, color: '#111827' },
  cardSub:  { fontSize: 13, color: '#6b7280', marginTop: 4 },
});
