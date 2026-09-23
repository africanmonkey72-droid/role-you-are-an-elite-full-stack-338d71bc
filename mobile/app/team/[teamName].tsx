import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Ionicons from '@expo/vector-icons/Ionicons';

import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';

import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchTeamTerminal } from '@/lib/api';
import type { EventTerminal } from '@/types/analytics';

export default function TeamTerminalScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ teamName: string }>();
  const teamName = decodeURIComponent(String(params.teamName ?? 'Team'));
  const [events, setEvents] = useState<EventTerminal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const load = useCallback(async () => { setLoading(true); try { setEvents(await fetchTeamTerminal(teamName)); setError(false); } catch { setError(true); } finally { setLoading(false); } }, [teamName]);
  useEffect(() => { void load(); }, [load]);
  return <Container><VStack gap="lg"><Pressable onPress={() => router.back()} accessibilityLabel="Go back"><HStack gap="xs" className="items-center"><Ionicons name="arrow-back" size={20} color="#007AFF" /><Text className="font-semibold text-primary">Back to scanner</Text></HStack></Pressable><VStack gap="xs"><Text className="text-xs font-semibold uppercase tracking-widest text-primary">Team terminal</Text><Text className="text-3xl font-bold">{teamName}</Text><Text className="text-sm text-text-secondary">Upcoming events, multi-venue pricing, and realized model performance.</Text></VStack>{loading ? <ActivityIndicator color="#007AFF" /> : error ? <Card><CardContent><Text className="font-semibold">Team terminal unavailable</Text></CardContent></Card> : events.length === 0 ? <Card><CardContent><Text className="font-semibold">No upcoming events found</Text></CardContent></Card> : events.map((event) => <Card key={event.event_id}><CardContent className="gap-3 p-4"><HStack className="items-center justify-between"><Chip>{event.league}</Chip><Text className="text-xs text-text-secondary">{event.status}</Text></HStack><Text className="text-lg font-bold">{event.matchup}</Text><Text className="text-xs text-text-secondary">{new Date(event.start_time).toLocaleString()}</Text>{event.markets.slice(0, 6).map((market) => <HStack key={`${market.provider}-${market.market_id}-${market.outcome}`} className="items-center justify-between"><View><Text className="font-medium">{market.outcome}</Text><Text className="text-xs text-text-secondary">{market.provider} · {market.share_price_cents.toFixed(1)}¢</Text></View><Text className={market.synthetic_edge && market.synthetic_edge > 0 ? 'font-semibold text-success' : 'text-text-secondary'}>{market.synthetic_edge == null ? '—' : `${market.synthetic_edge >= 0 ? '+' : ''}${(market.synthetic_edge * 100).toFixed(1)}%`}</Text></HStack>)}<HStack className="justify-between"><Text className="text-xs text-text-secondary">CLV {event.clv.closing_line_value_pct?.toFixed(2) ?? '0.00'}%</Text><Text className="text-xs text-text-secondary">Brier {event.model_performance.brier_score?.toFixed(3) ?? '—'}</Text><Text className="text-xs text-text-secondary">ROI {event.model_performance.roi_pct?.toFixed(1) ?? '0.0'}%</Text></HStack></CardContent></Card>)}</VStack></Container>;
}
