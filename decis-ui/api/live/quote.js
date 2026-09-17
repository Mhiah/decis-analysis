const BITGET_TICKERS = "https://api.bitget.com/api/v3/market/tickers";

function num(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const symbol = String(req.query.symbol || "")
    .trim()
    .toUpperCase();
  if (!symbol || !symbol.endsWith("USDT")) {
    res.status(400).json({
      ok: false,
      symbol,
      error: "symbol required, e.g. RJPMUSDT",
    });
    return;
  }

  try {
    const url = `${BITGET_TICKERS}?category=SPOT&symbol=${encodeURIComponent(symbol)}`;
    const upstream = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const body = await upstream.json();

    if (!upstream.ok || body.code !== "00000") {
      res.status(502).json({
        ok: false,
        symbol,
        error: body.msg || `Bitget HTTP ${upstream.status}`,
        retrievedAt: new Date().toISOString(),
      });
      return;
    }

    const row = (body.data && body.data[0]) || {};
    res.status(200).json({
      ok: true,
      symbol,
      source: "bitget",
      live: true,
      retrievedAt: new Date().toISOString(),
      lastPrice: num(row.lastPrice),
      bid: num(row.bid1Price),
      ask: num(row.ask1Price),
      change24h: num(row.price24hPcnt),
      high24h: num(row.highPrice24h),
      low24h: num(row.lowPrice24h),
      volume24h: num(row.volume24h),
      ts: row.ts,
    });
  } catch (err) {
    res.status(502).json({
      ok: false,
      symbol,
      error: err instanceof Error ? err.message : "quote fetch failed",
      retrievedAt: new Date().toISOString(),
    });
  }
};
