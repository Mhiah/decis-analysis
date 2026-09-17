export interface LiveQuote {
  ok: boolean;
  symbol: string;
  source?: string;
  live?: boolean;
  retrievedAt?: string;
  lastPrice?: number | null;
  bid?: number | null;
  ask?: number | null;
  change24h?: number | null;
  high24h?: number | null;
  low24h?: number | null;
  volume24h?: number | null;
  ts?: string;
  error?: string;
  errorKind?: string;
}

export async function fetchLiveQuote(symbol: string): Promise<LiveQuote> {
  const token = symbol.trim().toUpperCase();
  const res = await fetch(`/api/live/quote?symbol=${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  const data = (await res.json()) as LiveQuote;
  if (!res.ok && !data.error) {
    return { ok: false, symbol: token, error: `HTTP ${res.status}` };
  }
  return data;
}
