import { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { apiClient } from '../../services/api';
export default function SimbaScreen(){
  const[form,setForm]=useState({capacity:'100',watts:'60',hours:'4'});
  const[result,setResult]=useState<any>(null);
  const[loading,setLoading]=useState(false);
  async function calculate(){setLoading(true);try{const r=await apiClient.get('/simba/calculator?capacity_ah='+form.capacity+'&appliance_watts='+form.watts+'&usage_hours='+form.hours);setResult(r.data);}catch{setResult(null);}finally{setLoading(false);}}
  return(<ScrollView style={s.c} contentContainerStyle={s.content}>
    <Text style={s.title}>☀️ Simba — Solar Energy</Text>
    <View style={s.card}>
      <Text style={s.ct}>🔋 Battery Calculator</Text>
      {[['Battery Capacity (Ah)','capacity','100'],['Appliance Watts','watts','60'],['Daily Hours','hours','4']].map(([l,f,p])=>(
        <View key={f} style={s.ig}><Text style={s.label}>{l}</Text>
          <TextInput style={s.input} keyboardType="numeric" value={(form as any)[f]} placeholder={p} onChangeText={v=>setForm({...form,[f]:v})}/>
        </View>
      ))}
      <TouchableOpacity style={s.btn} onPress={calculate} disabled={loading}>{loading?<ActivityIndicator color="#fff"/>:<Text style={s.btnTxt}>Calculate</Text>}</TouchableOpacity>
      {result&&(<View style={s.result}><Text style={s.rv}>{result.runtime_days} days</Text><Text style={s.rs}>{result.recommendation}</Text></View>)}
    </View>
  </ScrollView>);
}
const s=StyleSheet.create({c:{flex:1,backgroundColor:'#f9fafb'},content:{padding:16},title:{fontSize:22,fontWeight:'700',color:'#111827',marginBottom:20},card:{backgroundColor:'#fff',borderRadius:16,padding:16,elevation:2},ct:{fontWeight:'700',fontSize:16,marginBottom:12},ig:{marginBottom:12},label:{fontSize:13,fontWeight:'600',color:'#374151',marginBottom:4},input:{borderWidth:1,borderColor:'#d1d5db',borderRadius:10,padding:10,fontSize:15},btn:{backgroundColor:'#E8A020',borderRadius:12,padding:14,alignItems:'center',marginTop:4},btnTxt:{color:'#fff',fontWeight:'700',fontSize:15},result:{backgroundColor:'#FEF3C7',borderRadius:12,padding:14,marginTop:12,alignItems:'center'},rv:{fontSize:32,fontWeight:'700',color:'#D97706',marginVertical:4},rs:{fontSize:13,color:'#78350F',textAlign:'center'}});
