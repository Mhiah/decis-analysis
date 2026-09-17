# Decis Analysis — AI Trading Desk

Bitget AI Hackathon · **AI Trading Desk** track.

AI processes IAA research artifacts (events, surprises, replay paths, calibration, cost bake-off). The trader keeps the final call. No live orders.

## Run for judges

See **DEMO.md** (host + timed script + screenshot checklist) and **CLAIMS.md** (honest claims). Talking points: **DEMO_NOTES.md**.

**Live market stays on for the whole demo** — prefer `desk/start_desk.ps1`, or leave `python desk/live_quotes.py` running in its own terminal.

```powershell
powershell -File desk/start_desk.ps1
# or:
python desk/live_quotes.py          # keep open
cd desk/decis-ui; npm run dev
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
