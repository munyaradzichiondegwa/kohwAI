import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { apiClient } from '../../services/api';
const SC:Record<string,string>={healthy:'#1A7A4A',sick:'#C0392B',recovered:'#1A5276',deceased:'#6b7280'};
export default function LivestockScreen(){
  const nav=useNavigation<any>();
  const[profiles,setProfiles]=useState<any[]>([]);
  const[loading,setLoading]=useState(true);
  useEffect(()=>{apiClient.get('/livestock/profiles').then(r=>setProfiles(r.data.profiles||[])).catch(()=>setProfiles([])).finally(()=>setLoading(false));},[]);
  return(<View style={s.c}>
    <View style={s.header}><Text style={s.title}>🐄 Livestock Health</Text>
      <TouchableOpacity style={s.addBtn} onPress={()=>nav.navigate('LiveDiag')}><Text style={s.addTxt}>🔍 AI Diagnose</Text></TouchableOpacity>
    </View>
    {loading&&<ActivityIndicator color="#784212" style={{marginTop:40}}/>}
    <FlatList data={profiles} keyExtractor={i=>i.id} contentContainerStyle={{padding:16}}
      ListEmptyComponent={!loading?(<View style={s.empty}><Text style={s.emptyIcon}>🐄</Text><Text style={s.emptyTxt}>No animals yet.</Text><Text style={s.emptyHint}>Add via web app, then diagnose here.</Text></View>):null}
      renderItem={({item})=>(<View style={s.card}>
        <View style={s.row}>
          <View><Text style={s.name}>{item.name}</Text><Text style={s.sub}>{item.animal_type}{item.breed?' · '+item.breed:''}</Text></View>
          <View style={[s.badge,{backgroundColor:SC[item.health_status]||'#6b7280'}]}><Text style={s.badgeTxt}>{item.health_status}</Text></View>
        </View>
        <TouchableOpacity style={s.diagBtn} onPress={()=>nav.navigate('LiveDiag')}><Text style={s.diagTxt}>📷 AI Diagnosis</Text></TouchableOpacity>
      </View>)}/>
  </View>);
}
const s=StyleSheet.create({c:{flex:1,backgroundColor:'#f9fafb'},header:{flexDirection:'row',justifyContent:'space-between',alignItems:'center',padding:16,backgroundColor:'#fff',borderBottomWidth:1,borderColor:'#e5e7eb'},title:{fontSize:20,fontWeight:'700',color:'#111827'},addBtn:{backgroundColor:'#784212',borderRadius:10,paddingHorizontal:12,paddingVertical:8},addTxt:{color:'#fff',fontSize:13,fontWeight:'600'},empty:{alignItems:'center',marginTop:60},emptyIcon:{fontSize:48},emptyTxt:{fontSize:16,fontWeight:'600',color:'#374151',marginTop:12},emptyHint:{fontSize:13,color:'#9ca3af',textAlign:'center',marginTop:6,paddingHorizontal:32},card:{backgroundColor:'#fff',borderRadius:16,padding:16,marginBottom:12,elevation:2},row:{flexDirection:'row',justifyContent:'space-between',alignItems:'flex-start'},name:{fontWeight:'700',fontSize:16,color:'#111827'},sub:{fontSize:13,color:'#6b7280',marginTop:2},badge:{borderRadius:20,paddingHorizontal:10,paddingVertical:4},badgeTxt:{color:'#fff',fontSize:11,fontWeight:'700'},diagBtn:{marginTop:12,backgroundColor:'#F5F0EC',borderRadius:10,padding:10,alignItems:'center',borderWidth:1,borderColor:'#784212'},diagTxt:{color:'#784212',fontSize:13,fontWeight:'600'}});
