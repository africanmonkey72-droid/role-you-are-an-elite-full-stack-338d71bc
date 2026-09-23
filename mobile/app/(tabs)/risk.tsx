import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { Card, CardContent } from '@/components/ui/Card';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchPortfolioSummary } from '@/lib/api';
import type { PortfolioSummary } from '@/types/analytics';

export default function RiskScreen() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => { setLoading(true); try { setSummary(await fetchPortfolioSummary()); } catch { setSummary(null); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  return <Container><VStack gap="lg"><VStack gap="xs"><Text className="text-xs font-semibold uppercase tracking-widest text-primary">Risk desk</Text><Text className="text-3xl font-bold">Portfolio controls</Text><Text className="text-sm text-text-secondary">Exposure, available capital, and position-level PnL in one view.</Text></VStack>{loading ? <ActivityIndicator color="#007AFF" /> : !summary ? <Card><CardContent><Text className="font-semibold">Risk summary unavailable</Text></CardContent></Card> : <><Card><CardContent className="gap-4 p-4"><HStack className="justify-between"><View><Text className="text-xs text-text-secondary">Bankroll</Text><Text className="text-2xl font-bold">${summary.bankroll.toLocaleString()}</Text></View><View><Text className="text-xs text-text-secondary">Available</Text><Text className="text-2xl font-bold text-success">${summary.available_capital.toLocaleString()}</Text></View></HStack><HStack className="justify-between"><Text className="text-sm text-text-secondary">Exposure</Text><Text className="font-semibold">{summary.exposure_pct.toFixed(1)}% / {summary.max_position_pct.toFixed(1)}%</Text></HStack><Text className="text-sm text-text-secondary">Unrealized PnL: <Text className={summary.unrealized_pnl >= 0 ? 'font-semibold text-success' : 'font-semibold text-error'}>{summary.unrealized_pnl >= 0 ? '+' : ''}${summary.unrealized_pnl.toFixed(2)}</Text></Text></CardContent></Card><Section title="Risk flags"><Card><CardContent className="gap-2 p-4">{summary.risk_flags.map((flag) => <Text key={flag} className="text-sm text-text-secondary">• {flag}</Text>)}</CardContent></Card></Section><Section title="Open positions"><Card><CardContent className="gap-3 p-4">{summary.positions.length === 0 ? <Text className="text-sm text-text-secondary">No live positions are currently recorded.</Text> : summary.positions.map((position) => <HStack key={position.id} className="items-center justify-between"><View><Text className="font-semibold">{position.selection}</Text><Text className="text-xs text-text-secondary">{position.provider} · ${position.stake.toFixed(0)} stake</Text></View><Text className={position.unrealized_pnl >= 0 ? 'font-semibold text-success' : 'font-semibold text-error'}>{position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}</Text></HStack>)}</CardContent></Card></Section></>}</VStack></Container>;
}
