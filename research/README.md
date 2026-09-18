# Research refresh kit

Vendored slim IAA modules + rolling artifacts for Decis Analysis scheduled refresh.

## Layout

- `iaa/` — SEC poll, Bitget candles, actuals, scoring, replay
- `data/` — `events_live.jsonl`, `event_scores_live.jsonl`, `replay_live.json`, `consensus_live.jsonl`, candle CSVs
- `posture.json` — frozen edge/calibration posture (not auto-updated)
- `refresh_research.py` — orchestrator used by GitHub Actions

## Local run

From the desk repo root (`desk/` / `decis-analysis`):

```powershell
$env:IAA_SEC_USER_AGENT = "Decis Analysis contact@example.com"
$env:PYTHONPATH = (Resolve-Path .\research).Path
python research/refresh_research.py
```

Hosted: GitHub Action every **3 hours** (see `.github/workflows/research-refresh.yml`).

Surprise values only appear when matching rows exist in `data/consensus_live.jsonl`.
