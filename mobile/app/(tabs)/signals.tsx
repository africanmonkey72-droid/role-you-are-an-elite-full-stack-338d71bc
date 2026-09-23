import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { ActivityIndicator, Pressable } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchSignals, markSignalRead } from '@/lib/api';
import type { SignalAlert } from '@/types/analytics';

export default function SignalsScreen() {
  const router = useRouter();
  const [signals, setSignals] = useState<SignalAlert[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => { setLoading(true); try { setSignals(await fetchSignals(unreadOnly)); } finally { setLoading(false); } }, [unreadOnly]);
  useEffect(() => { void load(); }, [load]);
  const read = async (signal: SignalAlert) => { try { await markSignalRead(signal.id); setSignals((items) => items.map((item) => item.id === signal.id ? { ...item, is_read: true } : item)); } catch { /* keep the alert visible */ } };
  return <Container><VStack gap="lg"><Section title="Signals" subtitle="Model, market, and risk alerts from the institutional desk."><HStack gap="sm"><Chip selected={!unreadOnly} onPress={() => setUnreadOnly(false)}>All</Chip><Chip selected={unreadOnly} onPress={() => setUnreadOnly(true)}>Unread</Chip></HStack><HStack gap="sm" className="mt-3"><Button size="sm" variant="secondary" onPress={() => router.push('/settings')}>Admin settings</Button><Button size="sm" variant="ghost" onPress={() => router.push('/trades')}>Trade history</Button></HStack></Section>{loading ? <ActivityIndicator color="#007AFF" /> : signals.length === 0 ? <Card><CardContent><Text className="font-semibold">No active signals</Text><Text className="mt-1 text-sm text-text-secondary">The desk is quiet for this filter.</Text></CardContent></Card> : signals.map((signal) => <Card key={signal.id}><CardContent className="gap-2 p-4"><HStack className="items-center justify-between"><Chip>{signal.severity}</Chip>{!signal.is_read ? <Pressable onPress={() => void read(signal)} accessibilityLabel="Mark signal as read"><Ionicons name="checkmark-circle-outline" size={24} color="#007AFF" /></Pressable> : <Ionicons name="checkmark-circle" size={22} color="#00A896" />}</HStack><Text className="font-semibold">{signal.signal_type}</Text><Text className="text-sm text-text-secondary">{signal.message}</Text><Text className="text-xs text-text-secondary">{new Date(signal.created_at).toLocaleString()}</Text></CardContent></Card>)}</VStack></Container>;
}
