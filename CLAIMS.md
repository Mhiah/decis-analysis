# Decis Analysis — Claims checklist

Track: Bitget AI Hackathon · **AI Trading Desk**  
Product: Decis Analysis  
One-liner: AI processes the research, argues against itself, and hands you the call.

## Claimed

| Claim | Status |
|-------|--------|
| Personalized workstation around research event packages | Proven |
| Structured signal: material / changed / implies | Proven |
| Decision stress-testing: thesis + bull / bear / invalidation | Proven |
| Human Hold / Review / Idea + optional note + journal | Proven |
| Constrained NL Q&A over structured desk objects | Proven |
| Live Bitget public ticker side panel (optional sidecar) | Proven when sidecar runs |
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

## Honesty notes

- Focus selector = earnings/event packages in `desk_snapshot`, not every Bitget rToken.
- Execution / review / develop are option A: UI + `localStorage` only.
- Live quotes are market context only; they do not drive signal or stress-test.
- Research packages refresh on a **3-hour GitHub Action** (SEC + Bitget). Surprise needs human/vendor consensus input; path needs candles after the event clock.
- Refresh does not flip `strategyEdgeValidated` or claim new edge.
