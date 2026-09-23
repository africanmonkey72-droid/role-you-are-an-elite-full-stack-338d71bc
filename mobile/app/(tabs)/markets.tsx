import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchMarkets } from '@/lib/api';
import type { MarketSnapshot, SportKey } from '@/types/analytics';

const SPORTS: SportKey[] = ['basketball', 'football', 'baseball', 'hockey', 'soccer', 'tennis', 'mma'];
function pct(value: number | null | undefined): string { return value == null ? '—' : `${(value * 100).toFixed(1)}%`; }

export default function MarketsScreen() {
  const [sport, setSport] = useState<SportKey>('basketball');
  const [provider, setProvider] = useState('all');
  const [markets, setMarkets] = useState<MarketSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const load = useCallback(async () => { setLoading(true); try { setMarkets(await fetchMarkets(sport, provider === 'all' ? undefined : provider)); setError(false); } catch { setError(true); } finally { setLoading(false); } }, [provider, sport]);
  useEffect(() => { void load(); }, [load]);
  return <Container><VStack gap="lg"><Section title="Live market matrix" subtitle="Compare share prices, sportsbook equivalents, depth, and synthetic edge."><HStack gap="sm" className="flex-wrap">{SPORTS.map((item) => <Chip key={item} selected={sport === item} onPress={() => setSport(item)}>{item.toUpperCase()}</Chip>)}</HStack><HStack gap="sm" className="mt-3"><Chip selected={provider === 'all'} onPress={() => setProvider('all')}>All venues</Chip><Chip selected={provider === 'polymarket'} onPress={() => setProvider('polymarket')}>Polymarket</Chip><Chip selected={provider === 'kalshi'} onPress={() => setProvider('kalshi')}>Kalshi</Chip></HStack></Section>{loading ? <ActivityIndicator color="#007AFF" /> : error ? <Card><CardContent><Text className="font-semibold">Market feed unavailable</Text><Text className="mt-1 text-sm text-text-secondary">The terminal will retry when the latest snapshots are available.</Text></CardContent></Card> : markets.length === 0 ? <Card><CardContent><Text className="font-semibold">No snapshots for this filter</Text></CardContent></Card> : markets.map((market) => <Card key={`${market.provider}-${market.market_id}-${market.outcome}`}><CardContent className="gap-2 p-4"><HStack className="items-center justify-between"><Text className="text-xs font-semibold uppercase text-primary">{market.provider}</Text><Text className="text-xs text-text-secondary">{market.market_id}</Text></HStack><Text className="font-semibold">{market.outcome}</Text><Text className="text-xs text-text-secondary">{market.question}</Text><HStack className="justify-between"><View><Text className="text-xs text-text-secondary">Share</Text><Text className="text-lg font-bold">{market.share_price_cents.toFixed(1)}¢</Text></View><View><Text className="text-xs text-text-secondary">Model</Text><Text className="text-lg font-bold">{pct(market.model_probability)}</Text></View><View><Text className="text-xs text-text-secondary">Edge</Text><Text className="text-lg font-bold text-success">{market.synthetic_edge == null ? '—' : `+${pct(market.synthetic_edge)}`}</Text></View></HStack><Text className="text-xs text-text-secondary">Bid {market.bid_cents?.toFixed(1) ?? '—'}¢ · Ask {market.ask_cents?.toFixed(1) ?? '—'}¢ · Liquidity ${Math.round(market.liquidity).toLocaleString()}</Text></CardContent></Card>)}</VStack></Container>;
}

