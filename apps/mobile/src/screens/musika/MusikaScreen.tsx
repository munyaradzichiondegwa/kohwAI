import { View, Text, StyleSheet, TouchableOpacity, FlatList, TextInput } from 'react-native';
import { useState, useEffect } from 'react';
import { apiClient } from '../../services/api';

export default function MusikaScreen() {
  const [listings, setListings] = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    apiClient.get('/musika/listings')
      .then(r => setListings(r.data.items || []))
      .catch(() => setListings([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <View style={s.c}>
      <Text style={s.title}>🛒 Musika — Marketplace</Text>
      <FlatList
        data={listings}
        keyExtractor={i => i.id}
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyTxt}>{loading ? 'Loading…' : 'No listings in your district yet.'}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={s.card}>
            <Text style={s.cardTitle}>{item.title}</Text>
            <Text style={s.cardSub}>{item.district} · {item.quantity} {item.unit}</Text>
            <Text style={s.price}>USD {item.priceUsd}</Text>
          </View>
        )}
      />
    </View>
  );
}

const s = StyleSheet.create({
  c:         { flex: 1, backgroundColor: '#f9fafb', padding: 16 },
  title:     { fontSize: 22, fontWeight: '700', color: '#111827', marginBottom: 16 },
  card:      { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 12, elevation: 2 },
  cardTitle: { fontWeight: '600', fontSize: 16 },
  cardSub:   { color: '#6b7280', fontSize: 13, marginTop: 2 },
  price:     { color: '#1A7A4A', fontWeight: '700', fontSize: 18, marginTop: 6 },
  empty:     { alignItems: 'center', marginTop: 60 },
  emptyTxt:  { color: '#9ca3af', fontSize: 15 },
});
