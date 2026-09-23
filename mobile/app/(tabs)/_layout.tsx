import { Tabs } from 'expo-router';
import { BottomTabBar } from '@react-navigation/bottom-tabs';
import type {
  BottomTabBarProps,
  BottomTabNavigationOptions,
} from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { View } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

type ExpoRouterTabOptions = BottomTabNavigationOptions & {
  href?: string | null;
};

function isRouteVisibleInTabBar(
  descriptors: BottomTabBarProps['descriptors'],
  route: BottomTabBarProps['state']['routes'][number]
) {
  const options = descriptors[route.key]?.options as
    | ExpoRouterTabOptions
    | undefined;
  return options?.href !== null;
}

export default function TabsLayout() {
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      initialRouteName="index"
      // CRITICAL: DO NOT REMOVE this tabBar prop — it auto-hides the tab bar when ≤1 visible tab.
      // Copy this exact pattern when rewriting this file. Single-tab bars look broken without it.
      tabBar={(props) => {
        const visibleRoutes = props.state.routes.filter(
          (route) => isRouteVisibleInTabBar(props.descriptors, route)
        );
        if (visibleRoutes.length <= 1) {
          return <View style={{ paddingBottom: insets.bottom }} />;
        }
        return <BottomTabBar {...props} />;
      }}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: '#FFFFFF' },
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: '#8E8E93',
        tabBarStyle: { backgroundColor: '#FFFFFF', borderTopColor: '#E5E5EA' },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size} color={color} /> }} />
      <Tabs.Screen name="opportunities" options={{ title: 'Scanner', tabBarIcon: ({ color, size }) => <Ionicons name="flash" size={size} color={color} /> }} />
      <Tabs.Screen name="markets" options={{ title: 'Markets', tabBarIcon: ({ color, size }) => <Ionicons name="bar-chart" size={size} color={color} /> }} />
      <Tabs.Screen name="signals" options={{ title: 'Signals', tabBarIcon: ({ color, size }) => <Ionicons name="notifications" size={size} color={color} /> }} />
      <Tabs.Screen name="risk" options={{ title: 'Risk', tabBarIcon: ({ color, size }) => <Ionicons name="shield-checkmark" size={size} color={color} /> }} />
      <Tabs.Screen name="breakdown" options={{ title: 'Breakdown', tabBarIcon: ({ color, size }) => <Ionicons name="analytics" size={size} color={color} /> }} />
    </Tabs>
  );
}
