import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { apiFetch } from '@/lib/api';
import type { SportAnalyticsBreakdown, SportKey } from '@/types/analytics';

const SPORTS: { key: SportKey; label: string }[] = [
  { key: 'basketball', label: 'Basketball' },
  { key: 'football', label: 'Football' },
  { key: 'baseball', label: 'Baseball' },
  { key: 'hockey', label: 'Hockey' },
  { key: 'soccer', label: 'Soccer' },
  { key: 'tennis', label: 'Tennis' },
  { key: 'mma', label: 'UFC / MMA' },
];

function formatMetric(value: number | string | boolean | null): string {
  if (value === null) return 'Not available';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    return value > 0 && value < 1 ? `${Math.round(value * 100)}%` : value.toFixed(2);
  }
  return value;
}

function MetricRow({
  label,
  value,
  risk,
}: {
  label: string;
  value: number | string | boolean | null;
  risk?: string | null;
}) {
  return (
    <View style={styles.metricRow}>
      <HStack className="items-center justify-between">
        <Text className="flex-1 text-sm text-text-secondary">{label}</Text>
        <HStack gap="sm" className="items-center">
          {risk ? <Text className="text-xs font-semibold text-warning">{risk}</Text> : null}
          <Text className="text-sm font-semibold">{formatMetric(value)}</Text>
        </HStack>
      </HStack>
    </View>
  );
}

export default function BreakdownScreen() {
  const [sport, setSport] = useState<SportKey>('basketball');
  const [breakdown, setBreakdown] = useState<SportAnalyticsBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadBreakdown = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiFetch<SportAnalyticsBreakdown>(
        `/analytics/breakdown?sport=${encodeURIComponent(sport)}`,
      );
      setBreakdown(response);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [sport]);

  useEffect(() => {
    void loadBreakdown();
  }, [loadBreakdown]);

  return (
    <Container>
      <VStack gap="lg">
        <Section
          title="Sport Analytics Breakdown"
          subtitle="Underlying performance signals, market coverage, and the factors most likely to break the forecast."
        >
          <View style={styles.selector}>
            <HStack gap="sm" className="flex-wrap">
              {SPORTS.map((item) => (
                <Chip key={item.key} selected={sport === item.key} onPress={() => setSport(item.key)}>
                  {item.label}
                </Chip>
              ))}
            </HStack>
          </View>
        </Section>

        {loading ? (
          <Card>
            <CardContent>
              <ActivityIndicator color="#007AFF" accessibilityLabel="Loading sport analytics" />
            </CardContent>
          </Card>
        ) : error || !breakdown ? (
          <Card>
            <CardContent>
              <Text className="font-semibold">Analytics are temporarily unavailable</Text>
              <Text className="mt-1 text-sm text-text-secondary">
                Refresh the matchup dashboard to try the latest sport data again.
              </Text>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardContent>
                <Text className="text-xl font-semibold">{breakdown.label}</Text>
                <Text className="mt-1 text-sm text-text-secondary">
                  Leagues: {breakdown.leagues.join(' · ')}
                </Text>
                <Text className="mt-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  Supported markets
                </Text>
                <Text className="mt-1 text-sm text-text-secondary">
                  {breakdown.markets.join(' · ')}
                </Text>
              </CardContent>
            </Card>

            <Section title="Underlying metrics" subtitle="The inputs feeding the probability distribution and value matrix.">
              <Card>
                <CardContent>
                  {breakdown.metrics.map((metric) => (
                    <MetricRow key={metric.key} label={metric.label} value={metric.value} risk={metric.risk} />
                  ))}
                </CardContent>
              </Card>
            </Section>

            <Section title="Loss factors" subtitle="Compare what can invalidate the favorite before placing a position.">
              <Card>
                <CardContent>
                  {breakdown.loss_factors.length === 0 ? (
                    <Text className="text-sm text-text-secondary">No elevated loss factors are currently flagged.</Text>
                  ) : (
                    breakdown.loss_factors.map((factor, index) => (
                      <View key={`${factor.key}-${index}`} style={styles.lossRow}>
                        <HStack className="items-center justify-between">
                          <Text className="flex-1 font-medium">{factor.label}</Text>
                          {factor.risk ? <Text className="text-xs font-semibold text-error">{factor.risk}</Text> : null}
                        </HStack>
                        <Text className="mt-1 text-sm text-text-secondary">{formatMetric(factor.value)}</Text>
                      </View>
                    ))
                  )}
                </CardContent>
              </Card>
            </Section>
          </>
        )}
      </VStack>
    </Container>
  );
}

const styles = StyleSheet.create({
  selector: {
    flexWrap: 'wrap',
    rowGap: 8,
    columnGap: 8,
  },
  metricRow: {
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#E5E5EA',
  },
  metricValue: {
    alignItems: 'center',
  },
  lossRow: {
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#E5E5EA',
  },
});
