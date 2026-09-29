# Decis Analysis — AI Trading Desk

> **AI processes the research, argues against itself, and hands you the call.**

**[Live desk](https://decis-analysis.vercel.app)** · **[Repo](https://github.com/Mhiah/decis-analysis)** · Bitget AI Hackathon S2 · **AI Trading Desk** track

**Decis Analysis** is a personalized research workstation for Bitget stock **rTokens** around earnings and related evidence. It turns a frozen research package (surprise, 180-minute path, event clock) into a structured signal and a stress-test, then leaves **Hold / Review / Idea** with the trader. Research comes from **IAA**, our SEC + Bitget research engine, and the **Ask** panel is answered by **Qwen** from the desk's own data. Live Bitget quotes sit beside the desk as **market context only**. No exchange orders. No proven-edge claim.

Docs: **[DEMO.md](./DEMO.md)** · **[CLAIMS.md](./CLAIMS.md)** · **[SPEC.md](./SPEC.md)**

---

## Why Decis

Most trading UIs either dump raw data or jump straight to an order. Earnings research and the rToken tape usually live in different places. Decis keeps them on one desk and stops before the submit button.

Bitget lists the rToken; EDGAR times the print; Decis puts surprise, path, and clock on one desk so a discretionary trader can decide without the system trading for them.

1. **Evidence before narrative.** Surprise (news), 180m path (absorption), and event clock (how soft t=0 is) share one panel.
2. **AI that argues against itself.** Signal (`material` / `changed` / `implies`) is followed by bull, bear, and invalidation.
3. **Human keeps the call.** Hold / Review / Idea are research audit actions. They never become Bitget tickets.
4. **Live ticker cannot hijack the thesis.** The Live market panel polls Bitget public quotes. It does not drive signal, stress-test, Ask, or the verdict strip.
5. **Honest research posture.** Calibration ran; cost-aware bake-off challengers took **zero** holdout trades. `strategyEdgeValidated: false`. Paper execution stayed blocked.

---

## IAA: the research behind Decis

**IAA** (Information Absorption Alpha) is the research engine Decis runs on. It lives in [`research/iaa/`](./research/iaa) and answers one question: *when a US company files its earnings with the SEC, how does its Bitget stock rToken react?*

It is read-only by design (`"IAA research prototype. No order execution capability."`). It has no order code and holds no exchange keys.

### What IAA does

| Step | Module | What it does |
|------|--------|--------------|
| 1. Find the print | `sec_events.py` | Polls SEC EDGAR for Item 2.02 (earnings) 8-K filings across the tracked universe (AAPL, NVDA, TSLA, MSFT, META, JPM and ~30 more) and records the EDGAR acceptance time |
| 2. Read the numbers | `actuals.py` | Pulls the earnings exhibit, hash-verifies it, and extracts the reported actuals |
| 3. Measure the surprise | `consensus.py`, `scoring.py` | Compares actuals with point-in-time consensus. Surprise is only scored when a real consensus row exists; otherwise it stays `—` |
| 4. Get the tape | `collector.py`, `event_market.py`, `providers.py` | Collects Bitget 1-minute rToken candles around each event, with coverage checks |
| 5. Line them up honestly | `alignment.py` | Anti-look-ahead alignment: the event clock (t=0) is never placed on a candle that closed before the filing was public |
| 6. Replay the reaction | `replay.py` | Replays the 180 minutes after t=0. This is the **180m path** on the desk |

### How we came about it

IAA came first. We built it to test a simple idea: that the gap between an earnings filing and the rToken's reaction could be traded. We collected 30 earnings events, scored them, replayed each one against real Bitget candles, and then ran a strict validation (calibration, a chronological holdout of 10 events, and a cost-aware bake-off against simple baselines).

The result was honest but not a trading edge. Holdout direction accuracy was 0.50. Once round-trip costs were included, every challenger strategy took **zero** holdout trades. Paper execution was also blocked, because Bitget does not provide historical bid/ask. The frozen verdict is in [`research/posture.json`](./research/posture.json): `strategyEdgeValidated: false`.

That changed what we built. The research was still useful: it tells a trader exactly *what happened* (surprise, path, clock) around a print. What it could not justify was letting a bot place the trade. So instead of an auto-trader, we turned IAA into **Decis**, a desk that puts the evidence in front of a human, argues against itself, and stops at **Hold / Review / Idea**.

IAA keeps running behind the desk. A GitHub Action runs its modules every 3 hours to pick up new SEC filings and Bitget candles (see [Scheduled research refresh](#scheduled-research-refresh)).

---

## Desk stages

| # | Stage | What it does |
|---|--------|----------------|
| 01 | **Workstation** | Focus an rToken; Event evidence + AI summary + Live market |
| 02 | **Signal generation** | Material, changed, implies |
| 03 | **Decision stress-testing** | Bull, bear, invalidation; Ask desk; Hold / Review / Idea |
| 04 | **Execution support** | Local size draft after Review/Idea — never sent |
| 05 | **Review & self-development** | Score the call; keep a playbook lesson on-device |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Decis UI (Vite + React + TypeScript)                       │
│  Focus · Event evidence · Live market · Signal · Stress     │
│  Ask · Hold/Review/Idea · Local ticket · Review/playbook    │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                │ /desk_snapshot.json         │ /api/live/quote
                │                             │
┌───────────────▼───────────────┐   ┌─────────▼────────────────┐
│  Research snapshot            │   │  Live quotes             │
│  public/desk_snapshot.json    │   │  Local: live_quotes.py   │
│  (surprise · path · clock ·   │   │  Hosted: Vercel serverless│
│   posture · 30 packages)      │   │  Bitget public market API │
└───────────────▲───────────────┘   └──────────────────────────┘
                │
┌───────────────┴──────────────────────────────────────────────┐
│  Research refresh (GitHub Action every 3h)                   │
│  SEC Item 2.02 poll → Bitget 1m candles → optional score     │
│  → 180m replay → rebuild snapshot → commit → Vercel redeploy │
└──────────────────────────────────────────────────────────────┘
```

### Strict separation: research vs market context

| Layer | Source | Drives signal? |
|-------|--------|----------------|
| **Event evidence** | Frozen / scheduled research snapshot | Yes |
| **Signal / stress / Ask** | Derived from snapshot objects only | Yes (advisory) |
| **Live market** | Bitget public ticker | **No** |
| **Hold / Review / Idea** | Human + `localStorage` | Research audit only |
| **Draft ticket / playbook** | Browser only | Never submitted |

---

## How it uses Bitget

Bitget created the **stock rToken** market Decis researches (e.g. `RJPMUSDT` for JPM). The desk is built for that surface — not for equities-only portals, and not for a full Bitget universe browser.

| Bitget surface | How Decis uses it |
|----------------|-------------------|
| **Public ticker** | Live market panel (last, bid/ask, 24h) on the focused rToken — context only |
| **Public 1m candles** | Historical windows around each event clock for the **180m path** replay |
| **Hosted quote route** | Vercel `/api/live/quote` (and local `live_quotes.py`) so the tape stays up without keys |

**What Bitget does *not* supply (and Decis does not invent):**

- SEC filings / Item 2.02 exhibits → pulled from **EDGAR**
- Pre-event consensus for Surprise → research rows (`consensus_live.jsonl`); without them Surprise stays `—`
- Historical bid/ask for paper fills → unavailable; paper execution stays **blocked**
- Order placement → **not used**. No Bitget order API, no Agent Hub trade tools, no API keys on the desk

**Bitget created the rToken tape; Decis joins that tape to earnings evidence and stops at the human call.** Live quotes never rewrite signal, stress-test, Ask, or Hold / Review / Idea.

**Claim boundaries (Bitget-facing)**

| Claim | Status |
|-------|--------|
| Public Bitget ticker beside research focus | Proven (when Live) |
| 180m path from Bitget 1m candles in research packages | Proven on seeded set |
| Scheduled refresh that can pull new SEC events + Bitget candles | Proven (Action) |
| Bitget order / paper fill / Agent Hub execution | **Not claimed** |
| Full Bitget Reality listing as Focus list | **Not claimed** (packages only) |

---

## Core research loop

1. **Select focus** — ticker + rToken + earnings event package (not the full Bitget listing).
2. **Read evidence** — Surprise · 180m path · Event clock (+ importance).
3. **Signal** — material / changed / implies.
4. **Stress-test** — bull · bear · invalidation.
5. **Ask (optional)** — plain-English questions answered by Qwen from desk objects only. No invented fills.
6. **Decide** — Hold / Review / Idea + optional note; local journal.
7. **Optional loop** — draft local ticket → post-trade review → promote lesson to playbook.

---

## Setup

### Hosted

Open **https://decis-analysis.vercel.app**

Confirm the Live market pill says **Live**.

### Local (Windows)

One-shot starter (starts live-quote sidecar if needed, then UI):

```powershell
cd desk
powershell -File .\start_desk.ps1
```

Or two terminals:

```powershell
# Terminal A — keep running
python desk/live_quotes.py

# Terminal B
cd desk/decis-ui
npm install   # first time only
npm run dev
```

Open the Local URL Vite prints (often `http://127.0.0.1:5173/`).

### Rebuild research snapshot

```powershell
python build_desk_snapshot.py
```

Prefers `research/data/*` when present; falls back to the seeded combined research set.

Full SEC refresh locally:

```powershell
$env:IAA_SEC_USER_AGENT = "IAA-Research/0.1 you@example.com"
$env:PYTHONPATH = (Resolve-Path .\research).Path
python research/refresh_research.py
```

---

## Scheduled research refresh

Workflow: [`.github/workflows/research-refresh.yml`](./.github/workflows/research-refresh.yml)

| Trigger | Behavior |
|---------|----------|
| Cron | Every **3 hours** |
| Manual | Actions → **Research refresh** → Run workflow |

What it does:

1. Polls SEC EDGAR for Item 2.02 filings in the tracked rToken universe.
2. Merges new events into `research/data/events_live.jsonl`.
3. Fetches Bitget 1m candle windows and replays when possible.
4. Scores surprise **only** when a consensus row exists in `consensus_live.jsonl`.
5. Rebuilds `decis-ui/public/desk_snapshot.json` and commits if changed (Vercel redeploys).

**Repo secret:** `IAA_SEC_USER_AGENT` (project name + contact email). The Action also falls back to the project’s established SEC identity if the secret is empty.

**Honest limits:**

- Surprise stays `—` until consensus is supplied (`researchStatus: pending_surprise`).
- Path may be incomplete until ~180 minutes of candles exist (`pending_path`).
- Refresh does **not** re-validate strategy edge or flip posture.

---

## Tech stack

| Area | Choice |
|------|--------|
| UI | React 19, TypeScript, Vite |
| Hosting | Vercel (`decis-ui` + serverless `/api/live/quote`, `/api/ask`) |
| AI (Ask) | Qwen via OpenAI-compatible API (Alibaba Cloud Model Studio or Bitget hackathon endpoint) |
| Live quotes | Python sidecar locally; Bitget public market API |
| Research | Python (`research/iaa/*`): SEC ingest, candles, actuals/scoring, 180m replay |
| Data contract | `schema/desk_snapshot.schema.json` → `desk_snapshot.json` |
| CI | GitHub Actions research refresh |
| Persistence | Decision journal / tickets / lessons in browser `localStorage` |

---

## Qwen in Ask

The **Ask** panel is powered by **Qwen**, Alibaba Cloud's large language model, added for the Bitget AI Hackathon S2 Qwen track. You can ask a question in plain English about the focused rToken, such as *"Why is the path negative?"* or *"What would invalidate this?"*, and Qwen answers from the desk itself.

### Why Qwen, and why only in Ask

The rest of the desk (signal, stress-test, AI summary) is deterministic code, so every number on screen traces back to IAA research. We wanted a language model where it helps most, which is explaining that research conversationally, without letting it invent facts or push trades. So Qwen gets a narrow job:

- **Desk objects only.** Qwen only sees the focused rToken's desk data (focus, signal, stress-test, evidence, AI summary). It is told never to use outside prices, news, or forecasts.
- **No orders, no edge claims.** It is told never to suggest placing, sizing, or timing a trade, and never to claim a proven edge (`strategyEdgeValidated: false`).
- **Checked answers.** Qwen must reply as JSON. Any source it cites that isn't on the desk's allow-list is dropped.
- **No silent fallback.** If Qwen is not configured or fails, Ask says so instead of making up an answer.

### How it works

`decis-ui/api/ask.js` is a Vercel serverless route. The shared logic in `decis-ui/api/_qwen.js` sends the question and the desk objects to Qwen through its OpenAI-compatible chat completions API. The API key stays on the server and never reaches the browser.

| Env var | Default | Notes |
|---------|---------|-------|
| `DASHSCOPE_API_KEY` | — | Required to turn Qwen on |
| `QWEN_MODEL` | `qwen-plus` | The hosted desk uses `qwen3.8-max` via the hackathon endpoint |
| `QWEN_BASE_URL` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | Bitget hackathon credits: `https://hackathon.bitgetops.com/v1`. Mainland Alibaba accounts: `https://dashscope.aliyuncs.com/compatible-mode/v1` |

Local: copy `decis-ui/.env.example` to `decis-ui/.env.local`, fill the key, run `npm run dev` (Vite serves `/api/ask` itself). Hosted: add the same vars in Vercel project settings, then redeploy.

---

## AI attribution

In line with an honest hackathon posture:

- **Product path:** Signal, stress-test, and AI summary are **deterministic code** over structured research objects. Ask is answered by **Qwen** (Alibaba Cloud Model Studio or the hackathon endpoint) from those same desk objects only; any cite it invents is dropped. Without a working key, Ask shows an error instead of an answer. See [Qwen in Ask](#qwen-in-ask).
- **Build path:** Cursor / coding assistants were used while implementing UI, Vercel quote wiring, and the research refresh kit.
- **Not claimed:** Agentic order placement, plain-English strategy → live execution, or proven alpha.

---

## What is built vs not built

### Built

- Focus selector over packaged research events
- Event evidence (surprise · 180m path · clock)
- AI summary card
- Live Bitget quote panel (local + Vercel)
- Signal generation + decision stress-testing
- Ask, answered by Qwen from desk objects only
- Hold / Review / Idea + journal
- Local execution draft + review / playbook
- FAQ + research request
- Mobile layout + **← Back home**
- Public host + 3-hour SEC refresh Action

### Not built (by design in v1)

- Live or paper Bitget order routing
- Broker fills / exchange post-trade blotter
- Automatic consensus vendor for every new print
- Minute-by-minute live path during the open 180m window
- Claiming `strategy_edge_validated` or rewriting the model from playbook lessons

---

## Validation snapshot (research, not live P&L)

Observed on the research set used to seed the desk:

- **30** earnings events with scores and 180-minute Bitget candle replays
- Chronological holdout **10** events
- Holdout direction accuracy **0.50** (observed)
- Holdout MAE of the linear surprise model **~0.042** (observed)
- After provisional round-trip cost stress (**~0.45%**, estimated policy fixture — not a Bitget fee schedule), calibrated and absorption challengers took **zero** holdout trades (observed)
- `strategyEdgeValidated: false` (observed)
- Paper execution refused: historical bid/ask unavailable (observed)

No live strategy Sharpe / Sortino / max drawdown / win rate is reported, because no exchange fills exist.

---

## Project layout

```text
decis-analysis/
├── decis-ui/                 # Vite React app (Vercel root)
│   ├── public/desk_snapshot.json
│   ├── api/live/quote.js     # Hosted Bitget quote
│   ├── api/ask.js            # Qwen Ask route (+ api/_qwen.js)
│   └── src/
├── research/                 # SEC + Bitget refresh kit
│   ├── refresh_research.py
│   ├── data/                 # events / scores / replay / consensus
│   └── iaa/                  # IAA research engine (see above)
├── .github/workflows/        # research-refresh.yml
├── live_quotes.py            # Local quote sidecar :8788
├── build_desk_snapshot.py
├── schema/desk_snapshot.schema.json
├── DEMO.md / CLAIMS.md / SPEC.md
└── README.md
```

---

## Roadmap

1. Keep the 3-hour SEC refresh healthy; expand consensus rows so new prints get Surprise.
2. Partial-path UX while candles are still filling the 180m window.
3. Optional paper path **only after** historical quotes and a validated edge gate — neither is true today.
4. Never promote local playbook lessons into silent strategy self-update without a human gate.

---

Built for **Bitget AI Hackathon S2** · **AI Trading Desk** · by **[Mhiah](https://github.com/Mhiah)**

**Live:** [decis-analysis.vercel.app](https://decis-analysis.vercel.app)
