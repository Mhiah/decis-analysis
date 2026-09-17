# Decis Analysis — Demo notes & talking points

Use this when building the demo pack / pitch. Product story: **AI processes the research, argues against itself, and hands you the call.** Human keeps Hold / Review / Idea. No exchange orders. No proven-edge claim.

---

## One-liner for judges

Decis is a research workstation for Bitget rTokens around earnings: structured signal → stress-test → your call. Live ticker is context only.

---

## Glossary (say these out loud)

### Surprise
How much the earnings print beat or missed expectations. Direction and size of the **news**.

### 180m path
The rToken’s return path over the **first 180 minutes (~3 hours)** after the event clock (t=0).  
- **180m** = 180-minute research horizon  
- **path** = observed returns over that window (first print → horizon), not a file path or road  

Compares **news** (surprise) vs **how the token absorbed it** (path).

### EDGAR acceptance
Timestamp when the SEC’s EDGAR system **accepted** the filing (e.g. 8-K Item 2.02).  
Used as the **event clock fallback** when a precise issuer press-release / wire time is not validated.  
Usually slightly **later** than true distribution — label it honestly (`EDGAR ACCEPTANCE`), never call it a validated issuer clock.

### Importance (HIGH / MEDIUM / …)
Research importance of the focus event — shown next to the clock label under the token selector.

### Live market
Public Bitget ticker for the focused rToken (last, bid/ask, 24h).  
**Market context only** — does **not** drive signal, stress-test, Ask desk, or Hold / Review / Idea.

### Hold / Review / Idea
Research audit actions only — never sent to Bitget.  
- **Hold** — leave it  
- **Review** — watchlist; not treating as actionable idea yet  
- **Idea** — log for later human work; still not an order  

### Draft ticket / post-trade / playbook
Option A: local worksheet + review + lessons on this device only. Never exchange submit.

---

## Why surprise, 180m path, and event clock share one panel

Same **event evidence** family — one box (styled like live market):

| Field | Job |
|--------|-----|
| Surprise | What the print claimed |
| 180m path | What the market did over ~3 hours |
| Event clock | How reliable t=0 is (EDGAR fallback vs issuer-validated) |

Importance sits as a pill on that panel. Live market stays a separate side panel (context only).

### AI summary / Signal / Ask
- **Event evidence** — raw numbers (surprise, 180m path, clock).
- **AI summary** — interpretive note only (agree/diverge, fade, clock soft/firm).
- **Signal generation** — structured material / changed / implies without re-dumping the panel numbers.
- **Ask** — queries AI summary, stress (bull/bear/invalidation), posture, clock; redirects “what’s material/changed” back to the panels.

---

## Why these belong on the dashboard

Without them you’d only have prose. Judges need:

1. **Surprise** — is there a material print?  
2. **180m path** — did the token confirm it?  
3. **Clock label** — is t=0 honest enough to trust that path?  

That trio is the research spine before stress-test and the human call. Live market is the side glance.

---

## Honesty lines (skeptic Qs)

- **Is this proven alpha?** No. Advisory research desk; you keep the call.  
- **What is EDGAR acceptance?** SEC acceptance time; fallback clock when issuer time isn’t validated.  
- **Does live ticker drive the signal?** No — market context only; signal comes from the frozen research snapshot.

---

## Demo walk (suggested)

1. Open desk → catchphrase: *Turn evidence into a clear call.*  
2. Pick a focus rToken → note clock + importance under selector.  
3. Point at event evidence panel: surprise · 180m path · event clock.  
4. AI research summary = material + changed + implies in one advisory paragraph.  
5. Signal → stress-test → Ask (constrained).  
6. Log Hold / Review / Idea (+ optional note); show journal.  
7. Optional: draft ticket → review → playbook (local only).  
8. Close: no edge claim, no order sent; live quotes = context only.

---

## Do not say

- Proven trading edge / alpha  
- NightDesk branding or “no human in the middle”  
- Live / paper orders to Bitget  
- Full Bitget universe as the focus list (research packages only)

---

*Captured 2026-09-16 from product/UI discussion. Submit script: **DEMO.md** (host, timed walk, screenshot checklist).*
