import { useEffect, useRef, useState } from "react";
import { fetchLiveQuote, type LiveQuote } from "../lib/bitgetLive";

interface LiveQuotesPanelProps {
  symbol: string;
  ticker: string;
  pollMs?: number;
  retryMs?: number;
}

function fmt(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

export function LiveQuotesPanel({
  symbol,
  ticker,
  pollMs = 8000,
  retryMs = 3000,
}: LiveQuotesPanelProps) {
  const [quote, setQuote] = useState<LiveQuote | null>(null);
  const [status, setStatus] = useState<"loading" | "live" | "error">("loading");
  const lastGood = useRef<LiveQuote | null>(null);

  useEffect(() => {
    let alive = true;
    let timer = 0;

    async function pull() {
      try {
        const next = await fetchLiveQuote(symbol);
        if (!alive) return;
        if (next.ok) {
          lastGood.current = next;
          setQuote(next);
          setStatus("live");
          timer = window.setTimeout(() => void pull(), pollMs);
        } else {
          setQuote(lastGood.current ?? next);
          setStatus(lastGood.current ? "live" : "error");
          timer = window.setTimeout(() => void pull(), retryMs);
        }
      } catch (err) {
        if (!alive) return;
        const failed: LiveQuote = {
          ok: false,
          symbol,
          error: err instanceof Error ? err.message : "quote fetch failed",
        };
        setQuote(lastGood.current ?? failed);
        setStatus(lastGood.current ? "live" : "error");
        timer = window.setTimeout(() => void pull(), retryMs);
      }
    }

    setStatus(lastGood.current?.symbol === symbol ? "live" : "loading");
    if (lastGood.current?.symbol !== symbol) {
      lastGood.current = null;
      setQuote(null);
    }
    void pull();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [symbol, pollMs, retryMs]);

  const shown = quote?.ok || lastGood.current ? quote ?? lastGood.current : quote;
  const change = shown?.change24h;
  const changeTone =
    change == null ? "" : change >= 0 ? "tone-up" : "tone-down";

  return (
    <aside className="live-quotes-panel" aria-label="Live Bitget quote">
      <div className="live-quotes-head">
        <div>
          <p className="eyebrow">Live market</p>
          <h2>
            {ticker} · {symbol}
          </h2>
        </div>
        <span className={`live-pill status-${status}`}>
          {status === "live" ? "Live" : status === "loading" ? "Polling…" : "Offline"}
        </span>
      </div>

      {status === "error" && !shown?.ok ? (
        <p className="live-error">
          {shown?.error ?? "Could not reach Bitget."}
          <span> Keep `python desk/live_quotes.py` running — retrying…</span>
        </p>
      ) : (
        <>
          <div className="live-glance">
            <p className="metric-label">Last</p>
            <p className="live-last tabular">{fmt(shown?.lastPrice, 4)}</p>
            <p className={`live-change tabular ${changeTone}`}>{pct(change)} 24h</p>
          </div>
          <dl className="live-grid live-grid-compact">
            <div>
              <dt>Bid</dt>
              <dd className="tabular">{fmt(shown?.bid, 4)}</dd>
            </div>
            <div>
              <dt>Ask</dt>
              <dd className="tabular">{fmt(shown?.ask, 4)}</dd>
            </div>
            <div>
              <dt>High</dt>
              <dd className="tabular">{fmt(shown?.high24h, 4)}</dd>
            </div>
            <div>
              <dt>Low</dt>
              <dd className="tabular">{fmt(shown?.low24h, 4)}</dd>
            </div>
          </dl>
        </>
      )}

      <p className="live-footnote">
        Public Bitget ticker · every {Math.round(pollMs / 1000)}s · market context only
      </p>
    </aside>
  );
}
