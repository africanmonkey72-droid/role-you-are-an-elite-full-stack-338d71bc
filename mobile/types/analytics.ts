export type SportKey = 'basketball' | 'football' | 'baseball' | 'hockey' | 'soccer' | 'tennis' | 'mma';

export type BreakdownMetric = {
  key: string;
  label: string;
  value: number | string | boolean | null;
  unit?: string | null;
  risk?: string | null;
};

export type SportAnalyticsBreakdown = {
  sport: SportKey | string;
  label: string;
  leagues: string[];
  markets: string[];
  metrics: BreakdownMetric[];
  loss_factors: BreakdownMetric[];
};

export type TeamSearchResult = {
  id: number;
  name: string;
  sport: SportKey | string;
  league: string;
  abbreviation: string | null;
};

export type MarketSnapshot = {
  provider: string;
  market_id: string;
  question: string;
  outcome: string;
  share_price_cents: number;
  bid_cents: number | null;
  ask_cents: number | null;
  liquidity: number;
  volume_24h: number;
  order_book: Record<string, unknown>;
  deep_link: string | null;
  captured_at: string;
  sportsbook?: string | null;
  american_odds?: number | null;
  line?: number | null;
  model_probability?: number | null;
  synthetic_edge?: number | null;
};

export type Opportunity = {
  id: string;
  event_id: number;
  sport: string;
  league: string;
  matchup: string;
  market: string;
  selection: string;
  provider: string;
  price: string;
  model_probability: number;
  market_probability: number;
  edge: number;
  ev_percent: number;
  confidence: number;
  liquidity: number;
  time_to_start_minutes: number;
  polymarket_link: string | null;
  sportsbook_link: string | null;
};

export type EventTerminal = {
  event_id: number;
  matchup: string;
  sport: string;
  league: string;
  start_time: string;
  status: string;
  markets: MarketSnapshot[];
  clv: Record<string, number>;
  model_performance: Record<string, number>;
};

export type SignalAlert = {
  id: number;
  event_id: number | null;
  signal_type: string;
  severity: string;
  message: string;
  payload: Record<string, unknown> | null;
  is_read: boolean;
  created_at: string;
};

export type PortfolioPosition = {
  id: number;
  instrument: string;
  provider: string;
  selection: string;
  stake: number;
  entry_price: number;
  model_probability: number;
  status: string;
  unrealized_pnl: number;
  risk_contribution: number;
};

export type PortfolioSummary = {
  portfolio_id: number;
  name: string;
  bankroll: number;
  invested: number;
  available_capital: number;
  unrealized_pnl: number;
  exposure_pct: number;
  max_position_pct: number;
  positions: PortfolioPosition[];
  risk_flags: string[];
};
