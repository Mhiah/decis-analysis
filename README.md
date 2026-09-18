# Decis Analysis — AI Trading Desk

Bitget AI Hackathon · **AI Trading Desk** track.

AI processes IAA research artifacts (events, surprises, replay paths, calibration, cost bake-off). The trader keeps the final call. No live orders.

## Live desk

**https://decis-analysis.vercel.app** — public Decis UI (Mhiah). Live market quotes via Bitget public API.

Repo: **https://github.com/Mhiah/decis-analysis**

## Run locally

See **DEMO.md** (host + timed script + screenshot checklist) and **CLAIMS.md** (honest claims). Talking points: **DEMO_NOTES.md**.

```powershell
powershell -File start_desk.ps1
# or:
python live_quotes.py
cd decis-ui; npm run dev
```

## Research snapshot

- Schema: `schema/desk_snapshot.schema.json`
- Snapshot: `data/desk_snapshot.json` (also copied to `decis-ui/public/`)
- Live research kit: `research/` (SEC poll, candles, scores, replay)

Rebuild locally (prefers `research/data/*` when present):

```powershell
python build_desk_snapshot.py
```

Full scheduled refresh (needs SEC user-agent):

```powershell
$env:IAA_SEC_USER_AGENT = "Decis Analysis you@example.com"
$env:PYTHONPATH = (Resolve-Path .\research).Path
python research/refresh_research.py
```

### GitHub Action (hosted desk)

Workflow: `.github/workflows/research-refresh.yml`

- Runs **every 3 hours** and on manual **workflow_dispatch**
- Polls SEC Item 2.02 for the rToken universe, enriches Bitget 1m windows, rebuilds snapshot, commits if changed (Vercel redeploys)
- Repo secret required: `IAA_SEC_USER_AGENT` (project name + contact email)

Surprise still needs a matching row in `research/data/consensus_live.jsonl`. Without consensus, new events can appear with Surprise as `—` and `researchStatus: pending_surprise`.

## Honest claims

- `strategyEdgeValidated: false` on the current challenger
- Paper / live remain blocked
- Desk is advisory: Hold / Review / Idea only
- Refresh does **not** re-validate strategy edge
