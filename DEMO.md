# Decis Analysis — Demo pack (Bitget AI Hackathon S2)

**Track:** AI Trading Desk  
**Product:** Decis Analysis  
**One-liner:** AI processes the research, argues against itself, and hands you the call.

Longer talking points / glossary: **DEMO_NOTES.md** · Honest claims: **CLAIMS.md**

---

## 1. Host / run (judges)

**Live market must stay up the whole demo.** Use the one-shot starter (starts sidecar if needed, then UI):

```powershell
cd desk
powershell -File .\start_desk.ps1
```

Or two terminals (leave both open):

```powershell
# Terminal A — keep running (live market)
python desk/live_quotes.py

# Terminal B — UI
cd desk/decis-ui
npm install   # first time only
npm run dev
```

Open the Local URL Vite prints (often `http://127.0.0.1:5173/` or `:5174/`).

Confirm Live market pill says **Live** before you present. If it says Offline, Terminal A died — restart `python desk/live_quotes.py`.

Optional snapshot rebuild:

```powershell
python build_desk_snapshot.py
```

Hosted research packages refresh via GitHub Action about **every 3 hours** (Actions → Research refresh → Run workflow). Set repo secret `IAA_SEC_USER_AGENT` first.

**Phone check:** same URL on LAN if needed; mobile layout is covered in `MOBILE.md`.

---

## 2. Pitch (~3–4 min)

### 0. Open (10s)

> “Decis Analysis — AI Trading Desk for Bitget rTokens. AI processes the research, argues against itself, and hands you the call. No live orders. No proven-edge claim.”

Point at footer: **BITGET AI HACKATHON S2** (and research updated time when present).

### 1. Workstation (45s)

1. Catchphrase / hero: *Turn evidence into a clear call.*
2. Open **Focus rToken** — pick a high-importance name (good demos: **JPM**, **INTC**, **GE**).
3. Event evidence panel: **Surprise** · **180m path** · **Event clock** (+ importance).
4. Say out loud:
   - Surprise = news beat/miss  
   - 180m path = what the rToken did in ~3 hours after t=0 (green = path up, red = path down)  
   - Clock = issuer-validated vs **EDGAR acceptance** fallback  
5. AI research summary (See more if needed).
6. Live market side panel = **context only** — does not drive signal.

### 2. Signal (35s)

Scroll to **Structured signal** — **material / changed / implies**.  
“Generated research read, not a raw dump.”

### 3. Stress-test (40s)

**Bull / bear / invalidation.**  
“AI argues the opposing case before you commit.”

### 4. Ask desk (30s)

Click **What’s the bear case?** or **What would invalidate this?**  
Show the cites line — answers stay on desk objects.

### 5. Your call (40s)

Read **Hold / Review / Idea**. Click one (+ optional note).  
Toast: logged locally — **not sent to exchange**.  
Open decision journal briefly.

Optional (if time): draft ticket → desk loop review → playbook lesson (all local).

### 6. Honesty + request (20s)

FAQ fold: skeptic questions (edge? live ticker? EDGAR? Bitget order?).  
Research request: only packaged names are on Focus; request others — up to 3 days, not instant.

### 7. Close (15s)

> “No edge claim, no live orders, no exchange post-trade in v1 — by design. Research workstation for Bitget rTokens.”

---

## 3. Judge checklist

- [ ] Focus selector switches research packages  
- [ ] Surprise / 180m path / event clock visible  
- [ ] Signal shows material / changed / implies  
- [ ] Stress-test shows bull + bear + invalidation  
- [ ] Ask returns a grounded answer with cites  
- [ ] Hold / Review / Idea logs without placing an order  
- [ ] Live quote (if sidecar up) does not change signal text  
- [ ] Claims stay honest — see **CLAIMS.md**

---

## 4. Screenshot checklist (submit pack)

Capture desktop (and one phone frame if easy):

| # | Shot | What to show |
|---|------|----------------|
| 1 | Hero + focus | Catchphrase, Focus rToken open, event evidence |
| 2 | AI + live | AI summary + live market panel |
| 3 | Signal | material / changed / implies |
| 4 | Stress | bull / bear / invalidation |
| 5 | Ask | answered question + cites |
| 6 | Verdict | Hold/Review/Idea strip + toast or journal |
| 7 | Honesty | FAQ open + research request + S2 footer |

Suggested save folder: `desk/demo-shots/` (create when capturing).

---

## 5. Do not say

- Proven trading edge / alpha  
- NightDesk / “no human in the middle”  
- Live or paper orders to Bitget  
- Full Bitget universe as the Focus list (research packages only)  
- That green/red on 180m means “agrees with surprise” (it means path up/down)

---

## 6. Glossary (30-second version)

| Term | Say |
|------|-----|
| Surprise | News beat or miss |
| 180m path | ~3h rToken return after event clock |
| EDGAR acceptance | SEC accept time used as t=0 when issuer clock isn’t validated |
| Hold / Review / Idea | Your research call — never an exchange order |
| Live market | Bitget ticker context only |

Full glossary: **DEMO_NOTES.md**.
