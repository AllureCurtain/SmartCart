import React, { useState } from 'react';
import { StyleSheet, TouchableOpacity, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import HomeScreen from './src/screens/HomeScreen';
import PreferenceScreen from './src/screens/PreferenceScreen';
import { colors, fontSize, spacing } from './src/theme/tokens';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');

  return (
    <SafeAreaView style={styles.container}>
      {activeTab === 'home' ? <HomeScreen /> : <PreferenceScreen />}

      <View style={styles.tabBar}>
        <TouchableOpacity
          style={styles.tab}
          onPress={() => setActiveTab('home')}
        >
          <Text style={[styles.tabText, activeTab === 'home' && styles.tabTextActive]}>
            首页
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.tab}
          onPress={() => setActiveTab('preference')}
        >
          <Text style={[styles.tabText, activeTab === 'preference' && styles.tabTextActive]}>
            偏好
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderTopColor: colors.hairline,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.l,
    alignItems: 'center',
  },
  tabText: {
    fontSize: fontSize.label,
    color: colors.meta,
    letterSpacing: 1,
  },
  tabTextActive: {
    color: colors.ink,
    fontWeight: '800',
  },
});

