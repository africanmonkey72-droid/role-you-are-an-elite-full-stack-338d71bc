import type {
  EventTerminal,
  MarketSnapshot,
  Opportunity,
  PortfolioSummary,
  SignalAlert,
  TeamSearchResult,
} from '@/types/analytics';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error('Analytics data is temporarily unavailable');
  }

  return response.json() as Promise<T>;
}

export function fetchOpportunities(sport?: string): Promise<Opportunity[]> {
  const query = sport ? `?sport=${encodeURIComponent(sport)}` : '';
  return apiFetch<Opportunity[]>(`/institutional/opportunities${query}`);
}

export function fetchMarkets(sport?: string, provider?: string): Promise<MarketSnapshot[]> {
  const params = new URLSearchParams();
  if (sport) params.set('sport', sport);
  if (provider) params.set('provider', provider);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiFetch<MarketSnapshot[]>(`/institutional/markets${query}`);
}

export interface InstitutionalSettings {
  id: number;
  organization_name: string;
  execution_mode: 'paper' | 'live';
  risk_preset: 'conservative' | 'balanced' | 'aggressive';
  max_trade_amount: number;
  authorized_admin_telegram_ids: string[];
  has_telegram_bot_token: boolean;
  has_polymarket_credentials: boolean;
  has_wallet_private_key: boolean;
  has_admin_security_pin: boolean;
  updated_at: string;
}

export interface InstitutionalSettingsUpdate {
  organization_name?: string;
  execution_mode?: 'paper' | 'live';
  risk_preset?: 'conservative' | 'balanced' | 'aggressive';
  max_trade_amount?: number;
  authorized_admin_telegram_ids?: string[];
  telegram_bot_token?: string;
  polymarket_api_key?: string;
  polymarket_api_secret?: string;
  polymarket_passphrase?: string;
  wallet_private_key?: string;
  admin_security_pin?: string;
}

export interface TradeHistoryItem {
  id: number;
  provider: string;
  instrument: string;
  condition_id: string | null;
  token_id: string;
  side: string;
  requested_price: number;
  executed_price: number | null;
  size: number;
  status: string;
  external_order_id: string | null;
  failure_reason: string | null;
  guardrail_result: { passed: boolean; expected_value: number; confidence: number; liquidity: number; reasons: string[] };
  requested_at: string;
  executed_at: string | null;
}

export function fetchInstitutionalSettings(): Promise<InstitutionalSettings> {
  return apiFetch<InstitutionalSettings>('/institutional/settings');
}

export function updateInstitutionalSettings(payload: InstitutionalSettingsUpdate, adminId?: string): Promise<InstitutionalSettings> {
  return apiFetch<InstitutionalSettings>('/institutional/settings', {
    method: 'PATCH',
    body: JSON.stringify(payload),
    headers: adminId ? { 'X-Admin-Telegram-ID': adminId } : undefined,
  });
}

export function fetchTradeHistory(): Promise<TradeHistoryItem[]> {
  return apiFetch<TradeHistoryItem[]>('/institutional/trades');
}

export function searchTeams(query: string, sport?: string): Promise<TeamSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  if (sport) params.set('sport', sport);
  return apiFetch<TeamSearchResult[]>(`/institutional/teams/search?${params.toString()}`);
}

export function fetchTeamTerminal(teamName: string): Promise<EventTerminal[]> {
  return apiFetch<EventTerminal[]>(`/institutional/teams/${encodeURIComponent(teamName)}/terminal`);
}

export function fetchSignals(unreadOnly = false): Promise<SignalAlert[]> {
  return apiFetch<SignalAlert[]>(`/institutional/signals?unread_only=${String(unreadOnly)}`);
}

export function markSignalRead(id: number, isRead = true): Promise<SignalAlert> {
  return apiFetch<SignalAlert>(`/institutional/signals/${id}/read`, {
    method: 'PATCH',
    body: JSON.stringify({ is_read: isRead }),
  });
}

export function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>('/institutional/portfolio/summary');
}
