import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import Ionicons from '@expo/vector-icons/Ionicons';

import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchOpportunities, searchTeams } from '@/lib/api';
import type { Opportunity, SportKey, TeamSearchResult } from '@/types/analytics';

const SPORTS: { key: SportKey; label: string }[] = [
  { key: 'basketball', label: 'NBA / NCAA' }, { key: 'football', label: 'NFL / NCAA' },
  { key: 'baseball', label: 'MLB' }, { key: 'hockey', label: 'NHL' },
  { key: 'soccer', label: 'Soccer' }, { key: 'tennis', label: 'Tennis' }, { key: 'mma', label: 'UFC' },
];

function pct(value: number): string { return `${(value * 100).toFixed(1)}%`; }

export default function OpportunitiesScreen() {
  const router = useRouter();
  const [sport, setSport] = useState<SportKey>('basketball');
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [teams, setTeams] = useState<TeamSearchResult[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setOpportunities(await fetchOpportunities(sport)); setError(false); } catch { setError(true); } finally { setLoading(false); }
  }, [sport]);
  useEffect(() => { void load(); }, [load]);

  const onSearch = useCallback(async (value: string) => {
    setQuery(value);
    if (value.trim().length < 2) { setTeams([]); return; }
    try { setTeams(await searchTeams(value, sport)); } catch { setTeams([]); }
  }, [sport]);

  return (
    <Container>
      <VStack gap="lg">
        <VStack gap="xs"><Text className="text-xs font-semibold uppercase tracking-widest text-primary">Quant terminal</Text><Text className="text-3xl font-bold">Top opportunities</Text><Text className="text-sm text-text-secondary">Screen sportsbook and prediction-market prices for model edge.</Text></VStack>
        <Section title="Team & athlete search" subtitle="Find a team terminal across supported leagues.">
          <View style={styles.searchWrap}><Ionicons name="search" size={18} color="#718096" /><TextInput value={query} onChangeText={(value) => void onSearch(value)} placeholder="Search teams, clubs, athletes" placeholderTextColor="#718096" style={styles.input} /></View>
          {teams.map((team) => <Pressable key={team.id} onPress={() => router.push(`/team/${encodeURIComponent(team.name)}`)} style={styles.teamRow}><View><Text className="font-semibold">{team.name}</Text><Text className="text-xs text-text-secondary">{team.league} · {team.sport}</Text></View><Ionicons name="chevron-forward" size={18} color="#718096" /></Pressable>)}
        </Section>
        <HStack gap="sm" className="flex-wrap">{SPORTS.map((item) => <Chip key={item.key} selected={sport === item.key} onPress={() => setSport(item.key)}>{item.label}</Chip>)}</HStack>
        {loading ? <ActivityIndicator color="#007AFF" /> : error ? <Card><CardContent><Text className="font-semibold">Scanner unavailable</Text><Text className="mt-1 text-sm text-text-secondary">Live opportunities will return when market data reconnects.</Text></CardContent></Card> : opportunities.length === 0 ? <Card><CardContent><Text className="font-semibold">No qualifying edges</Text><Text className="mt-1 text-sm text-text-secondary">Lower the edge threshold or check another sport.</Text></CardContent></Card> : opportunities.map((item) => <Card key={item.id}><CardContent className="gap-3 p-4"><HStack className="items-center justify-between"><Chip>{item.provider}</Chip><Text className="text-xs text-text-secondary">{item.time_to_start_minutes}m to start</Text></HStack><Text className="font-semibold">{item.selection}</Text><Text className="text-xs text-text-secondary">{item.matchup} · {item.market}</Text><HStack className="justify-between"><View><Text className="text-xs text-text-secondary">Model</Text><Text className="text-lg font-bold">{pct(item.model_probability)}</Text></View><View><Text className="text-xs text-text-secondary">Edge</Text><Text className="text-lg font-bold text-success">+{pct(item.edge)}</Text></View><View><Text className="text-xs text-text-secondary">EV</Text><Text className="text-lg font-bold text-success">+{item.ev_percent.toFixed(1)}%</Text></View></HStack><Text className="text-xs text-text-secondary">{item.price} · liquidity ${Math.round(item.liquidity).toLocaleString()}</Text></CardContent></Card>)}
      </VStack>
    </Container>
  );
}

const styles = StyleSheet.create({ searchWrap: { alignItems: 'center', backgroundColor: '#F2F5F8', borderColor: '#D9E2EC', borderRadius: 12, borderWidth: 1, flexDirection: 'row', gap: 8, paddingHorizontal: 12 }, input: { color: '#102A43', flex: 1, fontSize: 16, minHeight: 46 }, teamRow: { alignItems: 'center', borderBottomColor: '#E5E7EB', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 12 } });
