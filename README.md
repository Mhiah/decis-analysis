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

## Data contract (Step 2)

- Schema: `schema/desk_snapshot.schema.json`
- Snapshot: `data/desk_snapshot.json` (also copied to `decis-ui/public/`)

Rebuild from IAA artifacts (project root = `outputs/iaa`):

```powershell
python desk/build_desk_snapshot.py
```

## Honest claims

- `strategyEdgeValidated: false` on the current challenger
- Paper / live remain blocked
- Desk is advisory: Hold / Review / Idea only
