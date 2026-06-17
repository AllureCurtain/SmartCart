import React, { useState } from 'react';
import { StyleSheet, TouchableOpacity, Text, View, LogBox } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import HomeScreen from './src/screens/HomeScreen';
import PreferenceScreen from './src/screens/PreferenceScreen';
import { colors, fontSize, spacing } from './src/theme/tokens';

// 单手机架构下 AutoGLM 接管手机搜索期间，Expo Go 被压后台，Metro 的 HMR/WebSocket
// 心跳超时后 LogBox 会弹 "Cannot connect to Expo CLI"——属 SDK 56 已知开发期告警，
// 不影响功能（搜索/切回/Memory 均正常），生产构建本就无 LogBox。演示录制时屏蔽此噪声。
LogBox.ignoreAllLogs();

export default function App() {
  const [activeTab, setActiveTab] = useState('home');

  return (
    <SafeAreaProvider style={styles.provider}>
      <SafeAreaView style={styles.container}>
      {activeTab === 'home' ? <HomeScreen /> : <PreferenceScreen />}

      <View style={styles.tabBar} accessibilityRole="tablist">
        <TouchableOpacity
          style={styles.tab}
          onPress={() => setActiveTab('home')}
          accessibilityRole="tab"
          accessibilityLabel="首页"
          accessibilityState={{ selected: activeTab === 'home' }}
        >
          <Text style={[styles.tabText, activeTab === 'home' && styles.tabTextActive]}>
            首页
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.tab}
          onPress={() => setActiveTab('preference')}
          accessibilityRole="tab"
          accessibilityLabel="偏好"
          accessibilityState={{ selected: activeTab === 'preference' }}
        >
          <Text style={[styles.tabText, activeTab === 'preference' && styles.tabTextActive]}>
            偏好
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  provider: {
    flex: 1,
    backgroundColor: colors.bg,
  },
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
    minHeight: spacing.touchTarget,
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

