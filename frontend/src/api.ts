import axios from 'axios';

export const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
});

export type SymbolRow = {
  symbol: string;
  price_date: string;
  close: number;
  daily_return_pct: number;
  volatility_30d: number;
};

export type PricePoint = {
  price_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  daily_return_pct: number;
  moving_avg_7d: number;
  moving_avg_30d: number;
  volatility_30d: number;
};

export type Movement = {
  symbol: string;
  price_date: string;
  close: number;
  daily_return_pct: number;
};

export type VolatileRow = {
  symbol: string;
  price_date: string;
  close: number;
  volatility_30d: number;
};

export async function fetchSymbols(): Promise<SymbolRow[]> {
  const { data } = await api.get('/api/symbols');
  return data;
}

export async function fetchSymbolHistory(symbol: string, days = 30): Promise<{ symbol: string; days: number; data: PricePoint[] }> {
  const { data } = await api.get(`/api/symbol/${symbol}`, { params: { days } });
  return data;
}

export async function fetchTopMovers(): Promise<{ gainers: Movement[]; losers: Movement[] }> {
  const { data } = await api.get('/api/top-movers');
  return data;
}

export async function fetchMostVolatile(): Promise<VolatileRow[]> {
  const { data } = await api.get('/api/most-volatile');
  return data;
}

export function downloadCsv(symbol: string, days = 100) {
  window.open(`${API_BASE}/api/download/${symbol}.csv?days=${days}`, '_blank');
}
