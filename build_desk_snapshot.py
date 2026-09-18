"""Build Decis Analysis desk snapshot from research artifacts.

Prefer live research kit (research/data/*) when present; otherwise fall back to
IAA combined30 artifacts under the parent iaa project.

Outputs:
  desk/data/desk_snapshot.json
  desk/decis-ui/public/desk_snapshot.json

Run from desk / decis-analysis repo root:
  python build_desk_snapshot.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DESK = Path(__file__).resolve().parent
IAA_ROOT = DESK.parent  # outputs/iaa when running inside the monorepo
SCHEMA_VERSION = "1.0.0"


def latest(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"{folder}/{pattern}")
    return matches[-1]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def downsample_path(observations: list[dict], max_points: int = 64) -> list[dict]:
    if not observations:
        return []
    step = max(1, len(observations) // max_points)
    points = []
    for index, item in enumerate(observations):
        if index % step == 0 or index == len(observations) - 1:
            points.append(
                {
                    "t": round(float(item["elapsed_minutes"]), 2),
                    "ret": float(item["observed_return"]),
                }
            )
    return points


def research_status(surprise, horizon_return) -> str:
    has_surprise = surprise is not None
    has_path = horizon_return is not None
    if has_surprise and has_path:
        return "ready"
    if not has_path:
        return "pending_path"
    return "pending_surprise"


def load_posture() -> dict:
    posture_path = DESK / "research" / "posture.json"
    if posture_path.exists():
        raw = json.loads(posture_path.read_text(encoding="utf-8"))
        return {
            "strategyEdgeValidated": bool(raw.get("strategyEdgeValidated")),
            "calibrationSuccessful": bool(raw.get("calibrationSuccessful")),
            "paperExecutionValidated": bool(raw.get("paperExecutionValidated")),
            "refusalReasons": raw.get("refusalReasons") or [],
            "paperRefusalReasons": raw.get("paperRefusalReasons") or [],
            "holdoutDirectionAccuracy": raw.get("holdoutDirectionAccuracy"),
            "holdoutMae": raw.get("holdoutMae"),
        }

    # Fallback: parent IAA reports (local monorepo only).
    cal = json.loads(latest(IAA_ROOT / "reports", "calibration-*.json").read_text(encoding="utf-8"))
    benches = sorted((IAA_ROOT / "reports").glob("benchmark-*.json"))
    bench = json.loads(benches[-1].read_text(encoding="utf-8")) if benches else {}
    papers = sorted((IAA_ROOT / "reports").glob("paper-execution-*.json"))
    paper = json.loads(papers[-1].read_text(encoding="utf-8")) if papers else {}
    holdout = cal.get("holdout_metrics") or {}
    return {
        "strategyEdgeValidated": bool(bench.get("strategy_edge_validated")),
        "calibrationSuccessful": bool(cal.get("calibration_successful")),
        "paperExecutionValidated": bool(paper.get("paper_execution_validated")),
        "refusalReasons": bench.get("refusal_reasons") or [],
        "paperRefusalReasons": paper.get("refusal_reasons") or [],
        "holdoutDirectionAccuracy": holdout.get("direction_accuracy"),
        "holdoutMae": holdout.get("mae"),
    }


def resolve_sources(prefer_live: bool = True) -> tuple[list[dict], list[dict], dict, str]:
    live_events = DESK / "research" / "data" / "events_live.jsonl"
    live_scores = DESK / "research" / "data" / "event_scores_live.jsonl"
    live_replay = DESK / "research" / "data" / "replay_live.json"

    if prefer_live and live_events.exists() and live_replay.exists():
        events = load_jsonl(live_events)
        scores = load_jsonl(live_scores)
        replay = json.loads(live_replay.read_text(encoding="utf-8"))
        return events, scores, replay, "research_live"

    events = load_jsonl(IAA_ROOT / "data" / "events_sec_combined30.jsonl")
    scores = load_jsonl(IAA_ROOT / "data" / "event_scores_combined30.jsonl")
    replay = json.loads(
        (IAA_ROOT / "reports" / "replay-combined30.json").read_text(encoding="utf-8")
    )
    return events, scores, replay, "combined30_fallback"


def build_snapshot(prefer_live: bool = True) -> dict:
    events, scores, replay, source = resolve_sources(prefer_live=prefer_live)
    if not events:
        raise FileNotFoundError("No events found for desk snapshot")

    score_by = {item["event_id"]: item for item in scores}
    replay_by = {item["event_id"]: item for item in replay.get("replays", [])}
    posture = load_posture()

    instruments = []
    for event in events:
        score = score_by.get(event["event_id"], {})
        replay_row = replay_by.get(event["event_id"], {})
        observations = replay_row.get("observations") or []
        surprise = score.get("source_surprise_fraction")
        horizon = replay_row.get("horizon_observed_return")
        first = observations[0]["observed_return"] if observations else None
        instruments.append(
            {
                "eventId": event["event_id"],
                "ticker": event.get("underlying_ticker"),
                "token": event.get("token_symbol"),
                "publishedAt": event.get("published_at"),
                "timestampSemantics": event.get("timestamp_semantics") or "unknown",
                "issuerClockValidated": bool(event.get("issuer_release_time_validated")),
                "direction": score.get("direction") or "neutral",
                "surprise": surprise,
                "importance": score.get("importance") or "unknown",
                "horizonReturn": horizon,
                "firstReturn": first,
                "tradeBlockers": score.get("trade_blockers")
                or (["SURPRISE_NOT_AVAILABLE"] if surprise is None else []),
                "path": downsample_path(observations),
                "researchStatus": research_status(surprise, horizon),
            }
        )

    instruments.sort(key=lambda item: item["publishedAt"] or "")
    updated_at = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "schemaVersion": SCHEMA_VERSION,
        "product": "Decis Analysis",
        "track": "AI Trading Desk",
        "tagline": "AI processes the research. You make the call.",
        "updatedAt": updated_at,
        "posture": posture,
        "gates": {
            "events": len(instruments),
            "issuerClocksValidated": sum(
                1 for event in events if event.get("issuer_release_time_validated")
            ),
            "immutableConsensus": sum(
                1 for score in scores if score.get("immutable_consensus_snapshot")
            ),
            "calibration": (
                "accepted_fit_edge_refused"
                if posture.get("calibrationSuccessful")
                else "refused"
            ),
            "paper": (
                "blocked"
                if not posture.get("paperExecutionValidated")
                else "validated"
            ),
            "live": "blocked",
            "researchSource": source,
        },
        "instruments": instruments,
    }

    out_data = DESK / "data" / "desk_snapshot.json"
    out_public = DESK / "decis-ui" / "public" / "desk_snapshot.json"
    out_data.parent.mkdir(parents=True, exist_ok=True)
    out_public.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2)
    out_data.write_text(payload, encoding="utf-8")
    out_public.write_text(payload, encoding="utf-8")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": source,
        "output": str(out_data),
        "uiCopy": str(out_public),
        "instruments": len(instruments),
        "updatedAt": updated_at,
        "strategyEdgeValidated": snapshot["posture"]["strategyEdgeValidated"],
    }


def main() -> None:
    meta = build_snapshot(prefer_live=True)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
