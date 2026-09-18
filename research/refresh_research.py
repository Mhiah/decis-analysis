"""Scheduled research refresh for Decis Analysis.

Polls SEC for new Item 2.02 events, enriches Bitget candles / replay when possible,
scores surprise only when consensus rows exist, then rebuilds desk_snapshot.json.

Run from desk / decis-analysis repo root:
  set PYTHONPATH=research
  python research/refresh_research.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

DESK = Path(__file__).resolve().parents[1]
RESEARCH = Path(__file__).resolve().parent
DATA = RESEARCH / "data"
REPORTS = RESEARCH / "reports"

# Make vendored iaa importable when run as a script.
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from iaa.alignment import load_candles  # noqa: E402
from iaa.collector import INTERVAL_MS, collect_symbol  # noqa: E402
from iaa.event_market import event_window  # noqa: E402
from iaa.providers import BitgetProvider  # noqa: E402
from iaa.replay import replay_event  # noqa: E402
from iaa.scoring import score_events  # noqa: E402
from iaa.sec_events import EXPANDED_CIKS, EXTENSION_CIKS, SECProvider  # noqa: E402

LOOKBACK_DAYS = int(os.environ.get("IAA_REFRESH_LOOKBACK_DAYS", "30"))
HORIZON_MINUTES = 180
BEFORE_MINUTES = 15


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def merge_events(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], list[dict]]:
    by_id = {row["event_id"]: row for row in existing}
    added = []
    for row in incoming:
        event_id = row["event_id"]
        if event_id not in by_id:
            by_id[event_id] = row
            added.append(row)
        else:
            # Prefer newer exhibit evidence when SEC re-polls the same filing.
            by_id[event_id] = {**by_id[event_id], **row}
    merged = sorted(by_id.values(), key=lambda item: item.get("published_at") or "")
    return merged, added


def poll_sec(lookback_days: int = LOOKBACK_DAYS) -> tuple[list[dict], dict]:
    user_agent = os.environ.get("IAA_SEC_USER_AGENT", "").strip()
    summary = {
        "skipped": False,
        "reason": None,
        "discovered": 0,
        "errors": [],
    }
    if not user_agent or "@" not in user_agent:
        summary["skipped"] = True
        summary["reason"] = "IAA_SEC_USER_AGENT missing or invalid"
        return [], summary

    end = utc_now()
    start = end - timedelta(days=lookback_days)
    ciks = {**EXPANDED_CIKS, **EXTENSION_CIKS}
    provider = SECProvider(user_agent)
    discovered: list[dict] = []

    # Collect per-ticker so one issuer failure does not abort the whole refresh.
    for ticker, cik in ciks.items():
        try:
            events, _requests = provider.collect(
                start,
                end,
                receipt_latency_seconds=180,
                processing_seconds=15,
                ciks={ticker: cik},
            )
            discovered.extend(events)
        except Exception as exc:  # noqa: BLE001 — keep cron resilient
            summary["errors"].append(f"{ticker}: {type(exc).__name__}: {exc}")
    summary["discovered"] = len(discovered)
    return discovered, summary


def enrich_candles(events: list[dict], event_ids: set[str] | None = None) -> dict:
    """Fetch Bitget 1m windows for selected events (default: all)."""
    provider = BitgetProvider(dns_fallback=True)
    targets = [
        event
        for event in events
        if event_ids is None or event["event_id"] in event_ids
    ]
    results = []
    for event in targets:
        try:
            start_ms, end_ms = event_window(event, BEFORE_MINUTES, HORIZON_MINUTES)
            # Cap end at now so young events still get a partial path.
            now_ms = int(utc_now().timestamp() * 1000)
            end_ms = min(end_ms, (now_ms // INTERVAL_MS + 1) * INTERVAL_MS)
            out = DATA / f'{event["token_symbol"]}_1m.csv'
            collection = collect_symbol(
                provider,
                event["token_symbol"],
                start_ms,
                end_ms,
                out,
                preserve_outside_window=True,
            )
            results.append(
                {
                    "event_id": event["event_id"],
                    "token": event["token_symbol"],
                    "rows": collection.get("rows", 0),
                    "ok": True,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "event_id": event["event_id"],
                    "token": event.get("token_symbol"),
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "attempted": len(targets),
        "ok": sum(1 for row in results if row.get("ok")),
        "results": results,
    }


def try_score_new_events(events: list[dict], new_ids: set[str]) -> dict:
    """Extract actuals and score only when consensus_live.jsonl has matching rows."""
    from iaa.actuals import extract_metrics, verified_exhibit
    from iaa.consensus import calculate_surprise
    from urllib.request import Request, urlopen

    consensus = load_jsonl(DATA / "consensus_live.jsonl")
    if not consensus:
        return {"scored": 0, "reason": "no consensus rows"}

    consensus_ids = {row["event_id"] for row in consensus}
    targets = [
        event
        for event in events
        if event["event_id"] in new_ids and event["event_id"] in consensus_ids
    ]
    if not targets:
        return {"scored": 0, "reason": "no new events with consensus"}

    records = []
    surprises = []
    for event in targets:
        try:
            exhibits = event.get("earnings_exhibits") or []
            url = next(
                (item["source_url"] for item in exhibits if item.get("type") == "EX-99.1"),
                None,
            )
            if not url:
                continue
            request = Request(
                url,
                headers={
                    "User-Agent": os.environ.get(
                        "IAA_SEC_USER_AGENT", "Decis-Analysis refresh@local"
                    ),
                    "Accept-Encoding": "identity",
                },
            )
            with urlopen(request, timeout=30) as response:
                body = response.read()
            _exhibit, digest = verified_exhibit(event, body)
            metrics = extract_metrics(body, event["underlying_ticker"])
            extracted_at = utc_now().isoformat()
            for metric in metrics:
                records.append(
                    {
                        **metric,
                        "event_id": event["event_id"],
                        "source_url": url,
                        "source_sha256": digest,
                        "extracted_at": extracted_at,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            print(f"actuals skip {event['event_id']}: {exc}", file=sys.stderr)

    for estimate in consensus:
        actual = next(
            (
                record
                for record in records
                if record["event_id"] == estimate["event_id"]
                and record["metric"] == estimate["metric"]
                and record["fiscal_period"] == estimate["fiscal_period"]
            ),
            None,
        )
        if actual:
            surprises.append(
                {
                    "event_id": estimate["event_id"],
                    "metric": estimate["metric"],
                    "estimate": estimate["estimate"],
                    "actual": actual["value"],
                    "surprise_fraction": calculate_surprise(
                        estimate["estimate"], actual["value"]
                    ),
                    "consensus_id": estimate["consensus_id"],
                    "immutable_snapshot_validated": estimate[
                        "immutable_snapshot_validated"
                    ],
                }
            )

    if not surprises:
        return {"scored": 0, "reason": "no joinable surprises"}

    new_scores = score_events(surprises)
    existing = load_jsonl(DATA / "event_scores_live.jsonl")
    by_id = {row["event_id"]: row for row in existing}
    for score in new_scores:
        by_id[score["event_id"]] = score
    write_jsonl(DATA / "event_scores_live.jsonl", list(by_id.values()))
    return {"scored": len(new_scores), "event_ids": [s["event_id"] for s in new_scores]}


def replay_events(events: list[dict], event_ids: set[str] | None = None) -> dict:
    scores = load_jsonl(DATA / "event_scores_live.jsonl")
    score_by = {row["event_id"]: row for row in scores}
    replay_path = DATA / "replay_live.json"
    if replay_path.exists():
        report = json.loads(replay_path.read_text(encoding="utf-8"))
    else:
        report = {"replays": []}
    replay_by = {row["event_id"]: row for row in report.get("replays", [])}

    attempted = 0
    updated = 0
    errors = []
    for event in events:
        event_id = event["event_id"]
        if event_ids is not None and event_id not in event_ids:
            continue
        # Path-only packages: synthesize a neutral score stub so replay can run.
        score = score_by.get(event_id) or {
            "event_id": event_id,
            "direction": "neutral",
            "magnitude_fraction": 0.0,
            "trade_blockers": ["SURPRISE_NOT_AVAILABLE"],
        }
        candle_path = DATA / f'{event["token_symbol"]}_1m.csv'
        if not candle_path.exists():
            continue
        attempted += 1
        try:
            candles = load_candles(candle_path)
            replay_by[event_id] = replay_event(
                event, candles, score, horizon_minutes=HORIZON_MINUTES
            )
            updated += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{event_id}: {type(exc).__name__}: {exc}")

    report = {
        "created_at": utc_now().isoformat(),
        "synthetic": False,
        "replay_count": len(replay_by),
        "trade_count": 0,
        "execution_validated": False,
        "replays": list(replay_by.values()),
    }
    replay_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"attempted": attempted, "updated": updated, "errors": errors}


def rebuild_snapshot() -> dict:
    # Import builder from desk root.
    desk_root = str(DESK)
    if desk_root not in sys.path:
        sys.path.insert(0, desk_root)
    import build_desk_snapshot as builder

    return builder.build_snapshot(prefer_live=True)


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    existing = load_jsonl(DATA / "events_live.jsonl")
    discovered, sec_summary = poll_sec()
    events, added = merge_events(existing, discovered)
    write_jsonl(DATA / "events_live.jsonl", events)
    new_ids = {row["event_id"] for row in added}

    # Also refresh candles for recent events still inside / near the 180m window.
    recent_cutoff = utc_now() - timedelta(hours=6)
    young_ids = {
        row["event_id"]
        for row in events
        if row.get("published_at")
        and datetime.fromisoformat(row["published_at"].replace("Z", "+00:00"))
        >= recent_cutoff
    }
    candle_ids = new_ids | young_ids
    candle_summary = (
        enrich_candles(events, candle_ids) if candle_ids else {"attempted": 0, "ok": 0}
    )
    score_summary = try_score_new_events(events, new_ids) if new_ids else {"scored": 0}
    replay_ids = candle_ids or None
    # On first seed-only run with no new ids, skip replay rewrite to keep frozen paths.
    if new_ids or young_ids:
        replay_summary = replay_events(events, replay_ids)
    else:
        replay_summary = {"attempted": 0, "updated": 0, "skipped": True}

    snapshot_meta = rebuild_snapshot()

    summary = {
        "created_at": utc_now().isoformat(),
        "sec": sec_summary,
        "added_event_ids": sorted(new_ids),
        "candles": candle_summary,
        "scoring": score_summary,
        "replay": replay_summary,
        "snapshot": snapshot_meta,
    }
    out = REPORTS / f"refresh-{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
