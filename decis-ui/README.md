# Decis Analysis UI

Functional React workstation for the **AI Trading Desk** track.

## Run

```powershell
cd decis-ui
npm install
npm run dev
```

## Data

Loads `/desk_snapshot.json` from `public/` (30 IAA events). Rebuild from IAA root:

```powershell
python desk/build_desk_snapshot.py
```

Schema: `../schema/desk_snapshot.schema.json`

If the file is missing, falls back to a small placeholder in `src/lib/deskData.ts`.

## Swap to live API later

1. Keep `src/types/desk.ts` as the contract.
2. Replace `loadDeskSnapshot()` fetch target with your API.
3. Optionally replace `generateDeskView()` with a backend that returns `GeneratedDeskView`.
