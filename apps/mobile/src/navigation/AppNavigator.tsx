import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import LoginScreen    from '../screens/auth/LoginScreen';
import DashboardScreen from '../screens/DashboardScreen';
import ZundeScreen    from '../screens/zunde/ZundeScreen';
import CropDiagScreen from '../screens/zunde/CropDiagnosisScreen';
import LiveDiagScreen from '../screens/zunde/LivestockDiagnosisScreen';
import { useAuthStore } from '../stores/authStore';

const Stack = createNativeStackNavigator();
const Tab   = createBottomTabNavigator();

function TabNavigator() {
  return (
    <Tab.Navigator screenOptions={{ tabBarActiveTintColor: '#1A7A4A', headerShown: false }}>
      <Tab.Screen name="Dashboard" component={DashboardScreen}
        options={{ tabBarLabel: 'Home', tabBarIcon: () => <Text>🏠</Text> }} />
      <Tab.Screen name="Zunde" component={ZundeScreen}
        options={{ tabBarLabel: 'Zunde', tabBarIcon: () => <Text>🌾</Text> }} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const token = useAuthStore(s => s.accessToken);
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!token ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : (
          <>
            <Stack.Screen name="Main"      component={TabNavigator} />
            <Stack.Screen name="CropDiag"  component={CropDiagScreen}
              options={{ presentation: 'modal', headerShown: true, title: 'Crop Diagnosis' }} />
            <Stack.Screen name="LiveDiag"  component={LiveDiagScreen}
              options={{ presentation: 'modal', headerShown: true, title: 'Livestock Diagnosis' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
