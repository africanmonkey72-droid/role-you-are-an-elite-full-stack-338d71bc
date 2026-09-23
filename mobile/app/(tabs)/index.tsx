import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { apiFetch } from '@/lib/api';
import type { SportKey } from '@/types/analytics';

const SPORT_OPTIONS: { key: SportKey; label: string }[] = [
  { key: 'basketball', label: 'Basketball' },
  { key: 'football', label: 'Football' },
  { key: 'baseball', label: 'Baseball' },
  { key: 'hockey', label: 'Hockey' },
  { key: 'soccer', label: 'Soccer' },
  { key: 'tennis', label: 'Tennis' },
  { key: 'mma', label: 'UFC / MMA' },
];

type HistogramBin = { bucket: number; probability: number };
type ValueRow = {
  sportsbook: string;
  selection: string;
  american_odds: number;
  vig_adjusted_probability: number;
  model_probability: number;
  fair_american_odds: number | null;
  probability_edge: number;
  ev_percent: number;
  has_edge: boolean;
};
type Overview = {
  home_team: string;
  away_team: string;
  league: string;
  venue: string | null;
  start_time: string;
  weather: { temperature?: number; condition?: string } | null;
  injuries: { team: string; player: string; status: string; impact_points: number }[];
  reliability_score: number;
  edge_message: string;
  simulation: {
    home_win_probability: number;
    away_win_probability: number;
    total_mean: number;
    margin_interval_90: number[];
    total_interval_90: number[];
    margin_histogram: HistogramBin[];
    total_histogram: HistogramBin[];
  };
  value_matrix: ValueRow[];
};

const fallbackOverview: Overview = {
  home_team: 'Boston Celtics',
  away_team: 'Denver Nuggets',
  league: 'NBA',
  venue: 'TD Garden',
  start_time: new Date().toISOString(),
  weather: { temperature: 48, condition: 'Clear' },
  injuries: [{ team: 'Denver Nuggets', player: 'J. Murray', status: 'Questionable', impact_points: 2.8 }],
  reliability_score: 86.4,
  edge_message: 'Significant model edge identified.',
  simulation: {
    home_win_probability: 0.58,
    away_win_probability: 0.42,
    total_mean: 224.8,
    margin_interval_90: [-12.4, 19.3],
    total_interval_90: [202.2, 247.1],
    margin_histogram: [0.03, 0.05, 0.08, 0.12, 0.16, 0.19, 0.15, 0.1, 0.07, 0.03, 0.01, 0.01].map((probability, index) => ({ bucket: index, probability })),
    total_histogram: [0.02, 0.04, 0.07, 0.1, 0.14, 0.17, 0.16, 0.12, 0.09, 0.05, 0.03, 0.01].map((probability, index) => ({ bucket: index, probability })),
  },
  value_matrix: [
    { sportsbook: 'Market consensus', selection: 'Boston Celtics', american_odds: -118, vig_adjusted_probability: 0.545, model_probability: 0.58, fair_american_odds: -138, probability_edge: 0.035, ev_percent: 7.4, has_edge: true },
    { sportsbook: 'Market consensus', selection: 'Denver Nuggets', american_odds: 102, vig_adjusted_probability: 0.455, model_probability: 0.42, fair_american_odds: 138, probability_edge: -0.035, ev_percent: -14.2, has_edge: false },
  ],
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function signedPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
}

function formatStart(value: string): string {
  return new Date(value).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function DistributionBars({ bins, accent }: { bins: HistogramBin[]; accent: string }) {
  const max = Math.max(...bins.map((bin) => bin.probability), 0.01);
  return (
    <View style={styles.chart} accessibilityLabel="Simulation distribution chart">
      {bins.map((bin, index) => (
        <View key={`${bin.bucket}-${index}`} style={styles.barSlot}>
          <View style={[styles.bar, { height: `${Math.max(8, (bin.probability / max) * 100)}%`, backgroundColor: accent }]} />
        </View>
      ))}
    </View>
  );
}

export default function AnalyticsHomeScreen() {
  const [overview, setOverview] = useState<Overview>(fallbackOverview);
  const [scenario, setScenario] = useState('Base case');
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [selectedSport, setSelectedSport] = useState<SportKey>('basketball');

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiFetch<Overview>(
        `/analytics/overview?sport=${encodeURIComponent(selectedSport)}`,
      );
      setOverview(response);
      setUsingFallback(false);
    } catch {
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [selectedSport]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const bestValue = useMemo(() => overview.value_matrix.filter((row) => row.has_edge).sort((a, b) => b.ev_percent - a.ev_percent)[0], [overview.value_matrix]);
  const homeProbability = scenario === 'Pessimistic' ? Math.max(0, overview.simulation.home_win_probability - 0.06) : scenario === 'Optimistic' ? Math.min(1, overview.simulation.home_win_probability + 0.04) : overview.simulation.home_win_probability;

  return (
    <Container>
      <VStack gap="lg">
        <Section
          title="Sport selector"
          subtitle="Tune the model to the league and market context you are analyzing."
        >
          <View style={styles.sportSelector}>
            <HStack gap="sm" className="flex-wrap">
              {SPORT_OPTIONS.map((sport) => (
                <Chip
                  key={sport.key}
                  selected={selectedSport === sport.key}
                  onPress={() => setSelectedSport(sport.key)}
                >
                  {sport.label}
                </Chip>
              ))}
            </HStack>
          </View>
        </Section>
        <HStack className="items-center justify-between">
          <VStack gap="xs">
            <Text className="text-xs font-semibold uppercase tracking-widest text-primary">Probabilistic desk</Text>
            <Text className="text-3xl font-bold text-text">Market view</Text>
          </VStack>
          <Pressable onPress={() => void loadOverview()} style={styles.iconButton} accessibilityLabel="Refresh analytics">
            <Ionicons name="refresh" size={19} color="#243B53" />
          </Pressable>
        </HStack>

        <Card className="overflow-hidden">
          <CardContent className="gap-4 p-5">
            <HStack className="items-center justify-between">
              <Chip>{overview.league}</Chip>
              <Text className="text-xs text-muted-foreground">{formatStart(overview.start_time)}</Text>
            </HStack>
            <VStack gap="xs">
              <Text className="text-2xl font-bold text-text">{overview.home_team}</Text>
              <Text className="text-sm font-medium text-muted-foreground">vs. {overview.away_team}</Text>
            </VStack>
            <HStack gap="sm" className="flex-wrap">
              <Text className="text-xs text-muted-foreground">{overview.venue ?? 'Venue pending'}</Text>
              {overview.weather?.condition ? <Text className="text-xs text-muted-foreground">· {overview.weather.condition}</Text> : null}
            </HStack>
            <View style={styles.probabilityTrack}>
              <View style={[styles.probabilityHome, { width: `${homeProbability * 100}%` }]} />
            </View>
            <HStack className="justify-between">
              <Text className="text-sm font-semibold text-primary">{percent(homeProbability)} home win</Text>
              <Text className="text-sm text-muted-foreground">{percent(1 - homeProbability)} away</Text>
            </HStack>
          </CardContent>
        </Card>

        <Section title="Scenario lens" subtitle="Stress-test the forecast without hiding uncertainty.">
          <HStack gap="sm" className="flex-wrap">
            {['Base case', 'Optimistic', 'Pessimistic'].map((item) => <Chip key={item} selected={scenario === item} onPress={() => setScenario(item)}>{item}</Chip>)}
          </HStack>
        </Section>

        <Section title="Value matrix" subtitle="Model probability versus vig-adjusted market price.">
          <Card>
            <CardContent className="gap-3 p-4">
              {overview.value_matrix.map((row) => (
                <View key={`${row.sportsbook}-${row.selection}`} style={styles.valueRow}>
                  <View style={styles.valueName}>
                    <Text className="text-sm font-semibold text-text">{row.selection}</Text>
                    <Text className="text-xs text-muted-foreground">{row.sportsbook} · {row.american_odds > 0 ? `+${row.american_odds}` : row.american_odds}</Text>
                  </View>
                  <View style={styles.valueMetric}><Text className="text-xs text-muted-foreground">Model</Text><Text className="text-sm font-bold text-text">{percent(row.model_probability)}</Text></View>
                  <View style={styles.valueMetric}><Text className="text-xs text-muted-foreground">Edge</Text><Text className={`text-sm font-bold ${row.has_edge ? 'text-success' : 'text-muted-foreground'}`}>{signedPercent(row.probability_edge)}</Text></View>
                  <View style={styles.valueMetric}><Text className="text-xs text-muted-foreground">EV</Text><Text className={`text-sm font-bold ${row.has_edge ? 'text-success' : 'text-muted-foreground'}`}>{row.ev_percent >= 0 ? '+' : ''}{row.ev_percent.toFixed(1)}%</Text></View>
                </View>
              ))}
              <Text className="pt-1 text-xs font-medium text-muted-foreground">{bestValue ? `${bestValue.selection}: fair price ${bestValue.fair_american_odds && bestValue.fair_american_odds > 0 ? '+' : ''}${bestValue.fair_american_odds ?? '—'}.` : overview.edge_message}</Text>
            </CardContent>
          </Card>
        </Section>

        <Section title="Simulation distributions" subtitle="10,000 correlated outcomes; intervals are plausible ranges, not guarantees.">
          <VStack gap="md">
            <Card><CardContent className="gap-2 p-4"><HStack className="justify-between"><Text className="font-semibold text-text">Margin of victory</Text><Text className="text-xs text-muted-foreground">90%: {overview.simulation.margin_interval_90[0]} to {overview.simulation.margin_interval_90[1]}</Text></HStack><DistributionBars bins={overview.simulation.margin_histogram} accent="#2F80ED" /></CardContent></Card>
            <Card><CardContent className="gap-2 p-4"><HStack className="justify-between"><Text className="font-semibold text-text">Total points</Text><Text className="text-xs text-muted-foreground">Mean {overview.simulation.total_mean.toFixed(1)}</Text></HStack><DistributionBars bins={overview.simulation.total_histogram} accent="#00A896" /></CardContent></Card>
          </VStack>
        </Section>

        <Card className="bg-primary/10"><CardContent className="gap-2 p-4"><HStack className="items-center justify-between"><Text className="font-semibold text-text">Input reliability</Text><Text className="text-lg font-bold text-primary">{overview.reliability_score.toFixed(1)}/100</Text></HStack><View style={styles.reliabilityTrack}><View style={[styles.reliabilityFill, { width: `${overview.reliability_score}%` }]} /></View><Text className="text-xs text-muted-foreground">Based on odds recency, injury freshness, sample size, and market stability.</Text></CardContent></Card>

        {overview.injuries.length > 0 ? <Section title="Availability watch" subtitle="Latest contextual inputs affecting the distribution."><Card><CardContent className="gap-3 p-4">{overview.injuries.map((injury) => <HStack key={`${injury.team}-${injury.player}`} className="items-center justify-between"><View><Text className="font-semibold text-text">{injury.player}</Text><Text className="text-xs text-muted-foreground">{injury.team} · {injury.status}</Text></View><Text className="text-sm font-semibold text-warning">-{injury.impact_points.toFixed(1)} pts</Text></HStack>)}</CardContent></Card></Section> : null}

        {usingFallback ? <Text className="text-center text-xs text-muted-foreground">Showing the latest illustrative model snapshot while live data reconnects.</Text> : null}
        {loading ? <ActivityIndicator color="#2F80ED" accessibilityLabel="Loading analytics" /> : <Button variant="secondary" onPress={() => void loadOverview()}>Refresh model snapshot</Button>}
      </VStack>
    </Container>
  );
}

const styles = StyleSheet.create({
  sportSelector: {
    flexWrap: 'wrap',
    rowGap: 8,
    columnGap: 8,
  },
  iconButton: { alignItems: 'center', backgroundColor: '#EAF2FF', borderRadius: 22, height: 44, justifyContent: 'center', width: 44 },
  probabilityTrack: { backgroundColor: '#E7EEF7', borderRadius: 10, height: 10, overflow: 'hidden', width: '100%' },
  probabilityHome: { backgroundColor: '#2F80ED', borderRadius: 10, height: '100%' },
  valueRow: { alignItems: 'center', borderBottomColor: '#E6EDF5', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', gap: 8, paddingVertical: 10 },
  valueName: { flex: 1 },
  valueMetric: { alignItems: 'flex-end', minWidth: 45 },
  chart: { alignItems: 'flex-end', flexDirection: 'row', gap: 4, height: 92, paddingTop: 12 },
  barSlot: { alignItems: 'center', flex: 1, height: '100%', justifyContent: 'flex-end' },
  bar: { borderRadius: 4, minHeight: 6, width: '80%' },
  reliabilityTrack: { backgroundColor: '#D7E7FF', borderRadius: 8, height: 8, overflow: 'hidden' },
  reliabilityFill: { backgroundColor: '#2F80ED', borderRadius: 8, height: '100%' },
});
