# Decis Analysis — Claims checklist

Track: Bitget AI Hackathon · **AI Trading Desk**  
Product: Decis Analysis  
One-liner: AI processes the research, argues against itself, and hands you the call.  
Research engine: **IAA** (`research/iaa/`) · Ask model: **Qwen**

## Claimed

| Claim | Status |
|-------|--------|
| Personalized workstation around research event packages | Proven |
| Structured signal: material / changed / implies | Proven |
| Decision stress-testing: thesis + bull / bear / invalidation | Proven |
| Human Hold / Review / Idea + optional note + journal | Proven |
| IAA research: SEC Item 2.02 events, hash-verified actuals, surprise, Bitget 1m candles, anti-look-ahead alignment, 180m replay | Proven on 30 seeded events |
| IAA edge validation ran (calibration, 10-event holdout, cost-aware bake-off) and was published as a failure | Proven (`strategyEdgeValidated: false`) |
| Ask: plain-English Q&A answered by **Qwen** from the focused rToken's desk objects only | Proven when a Qwen key is set |
| Qwen guardrails: no outside data, no order or sizing advice, no edge claims, JSON reply, invented cites dropped | Proven (server-side in `decis-ui/api/_qwen.js`) |
| Ask has no template fallback: if Qwen is unavailable it says so | Proven |
| Live Bitget public ticker side panel (hosted Vercel route or local sidecar) | Proven when Live |
| Execution support — local draft ticket only | Proven (never sent) |
| Post-trade review & self-development (one section) | Proven — local only |

## Not claimed

| Claim | Status |
|-------|--------|
| Proven trading edge / alpha | **Not claimed** |
| Live or paper order placement to Bitget | **Not claimed** |
| Broker fills / exchange post-trade blotter | **Not claimed** |
| Full Bitget Reality universe as focus list | **Not claimed** (research packages only) |
| Automated strategy self-update from lessons | **Not claimed** |
| Qwen generating the signal, stress-test, or AI summary | **Not claimed** (those are deterministic code) |
| Qwen using live prices, news, or knowledge outside the desk | **Not claimed** |

## Honesty notes

- Decis came out of IAA. IAA was built to test whether the rToken reaction to earnings filings could be traded. It found no edge after costs (holdout direction accuracy 0.50; challengers took zero holdout trades), so the research became a desk that leaves the call with a human.
- Ask is the only place a language model answers. Qwen sees desk objects only; the API key stays on the server. Citations are checked but not shown in the UI.
- Focus selector = earnings/event packages in `desk_snapshot`, not every Bitget rToken.
- Execution / review / develop are option A: UI + `localStorage` only.
- Live quotes are market context only; they do not drive signal or stress-test.
- Research packages refresh on a **3-hour GitHub Action** (SEC + Bitget). Surprise needs human/vendor consensus input; path needs candles after the event clock.
- Refresh does not flip `strategyEdgeValidated` or claim new edge.
