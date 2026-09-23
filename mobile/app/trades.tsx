import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator } from 'react-native';

import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchTradeHistory } from '@/lib/api';
import type { TradeHistoryItem } from '@/lib/api';

export default function TradesScreen() {
  const [trades, setTrades] = useState<TradeHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);


  const load = useCallback(async () => {
    try { setTrades(await fetchTradeHistory()); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return (
    <Container>
      <VStack gap="lg">
        <Section title="Trade history" subtitle="Every request, guardrail decision, and execution status in one place."><Text /></Section>
        {loading ? <ActivityIndicator color="#007AFF" /> : trades.length === 0 ? <Card><CardContent><Text className="font-semibold">No trades recorded</Text><Text className="mt-1 text-sm text-text-secondary">Guarded paper and live executions will appear here.</Text></CardContent></Card> : trades.map((trade) => (
          <Card key={trade.id}><CardContent className="gap-2 p-4">
            <Text className="font-semibold">{trade.side} · {trade.size} shares</Text>
            <Text className="text-sm text-text-secondary">{trade.provider} · {trade.token_id}</Text>
            <Text className="text-sm text-text-secondary">Requested {(trade.requested_price * 100).toFixed(1)}¢{trade.executed_price ? ` · Executed ${(trade.executed_price * 100).toFixed(1)}¢` : ''}</Text>
            <Chip selected={trade.status === 'filled' || trade.status === 'submitted'}>{trade.status}</Chip>
            {trade.failure_reason ? <Text className="text-sm text-text-secondary">{trade.failure_reason}</Text> : null}
            <Text className="text-xs text-text-secondary">{new Date(trade.requested_at).toLocaleString()}</Text>
          </CardContent></Card>
        ))}
      </VStack>
    </Container>
  );
}
